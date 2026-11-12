from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_staff
from ..models import Feedback, User
from ..schemas import FeedbackIn
from ..serializers import feedback_out
from ..utils import local_now, today, week_start_of

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

CATEGORIES = {
    "taste": "口味咸淡",
    "oil": "菜品太油",
    "fresh": "食材新鲜度",
    "hygiene": "卫生问题",
    "tableware": "餐具问题",
    "other": "其他建议",
}


@router.post("")
def create_feedback(
    payload: FeedbackIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="反馈类型不正确")
    text = payload.content.strip()
    if len(text) < 2:
        raise HTTPException(status_code=400, detail="请再多写几个字，方便我们改进")
    row = Feedback(
        user_id=user.id,
        category=payload.category,
        content=text,
        date=today(),
        meal=(payload.meal or "").strip() or "",
    )
    db.add(row)
    db.commit()
    return {"message": "反馈已匿名提交，感谢你的建议", "id": row.id}


@router.get("/mine")
def my_feedback(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Feedback)
        .filter(Feedback.user_id == user.id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .all()
    )
    return [feedback_out(r) for r in rows]


@router.get("")
def list_feedback(
    start: date | None = None,
    end: date | None = None,
    category: str = "",
    handled: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    query = db.query(Feedback)
    if start:
        query = query.filter(Feedback.date >= start)
    if end:
        query = query.filter(Feedback.date <= end)
    if category:
        query = query.filter(Feedback.category == category)
    if handled in ("true", "false"):
        query = query.filter(Feedback.handled.is_(handled == "true"))
    total = query.count()
    rows = (
        query.order_by(Feedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {**feedback_out(r), "category_label": CATEGORIES.get(r.category, "其他建议")} for r in rows
        ],
    }


@router.put("/{feedback_id}/handled")
def mark_handled(
    feedback_id: int,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """标记为已处理。单向操作：已处理的反馈不能退回待处理。"""
    row = db.get(Feedback, feedback_id)
    if row is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    if row.handled:
        return {"message": "该反馈已经是已处理状态", "handled": True, "pending": _pending_count(db)}
    row.handled = True
    db.commit()
    return {"message": "已标记为已处理", "handled": True, "pending": _pending_count(db)}


def _pending_count(db: Session) -> int:
    return db.query(func.count(Feedback.id)).filter(Feedback.handled.is_(False)).scalar() or 0


@router.get("/pending")
def pending_feedback(_: User = Depends(require_staff), db: Session = Depends(get_db)):
    """侧边导航小红点用的待处理数量。"""
    return {"pending": _pending_count(db)}


@router.get("/stats")
def feedback_stats(
    start: date | None = None,
    end: date | None = None,
    days: int = Query(30, ge=1, le=365),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    end = end or week_start_of(today()) + timedelta(days=6)
    start = start or week_start_of(today())
    if end < start:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if (end - start).days > 365:
        raise HTTPException(status_code=400, detail="统计区间不能超过一年")
    rows = db.query(Feedback).filter(Feedback.date >= start, Feedback.date <= end).all()
    by_category = {key: 0 for key in CATEGORIES}
    by_day: dict[str, int] = {}
    handled = 0
    for row in rows:
        by_category[row.category] = by_category.get(row.category, 0) + 1
        by_day[row.date.isoformat()] = by_day.get(row.date.isoformat(), 0) + 1
        if row.handled:
            handled += 1
    series = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        series.append({"date": d.isoformat(), "count": by_day.get(d.isoformat(), 0)})
    this_week_start = today() - timedelta(days=today().weekday())
    this_week = sum(1 for r in rows if r.date >= this_week_start)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total": len(rows),
        "handled": handled,
        "pending": len(rows) - handled,
        "pending_all": _pending_count(db),
        "this_week": this_week,
        "by_category": [
            {"key": k, "label": v, "count": by_category.get(k, 0)} for k, v in CATEGORIES.items()
        ],
        "series": series,
    }
