from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import MEAL_LABELS
from ..database import get_db
from ..deps import get_any_user, get_current_user, require_staff
from ..models import Menu, User, Vote
from ..schemas import VoteIn
from ..serializers import vote_out
from ..utils import all_settings, json_loads, today, week_start_of

router = APIRouter(prefix="/api/votes", tags=["votes"])


def _week_bounds(week_start: date) -> tuple[date, date]:
    start = week_start_of(week_start)
    return start, start + timedelta(days=6)


def _voting_window(settings: dict) -> tuple[date, date]:
    current = week_start_of(today())
    if not settings.get("vote_enabled", True):
        return current, current - timedelta(days=1)
    # 可为本週及下一周投票
    return current, current + timedelta(days=7)


def _week_dishes(db: Session, start: date) -> list[dict]:
    rows = (
        db.query(Menu)
        .filter(Menu.date >= start, Menu.date <= start + timedelta(days=6))
        .order_by(Menu.date.asc(), Menu.meal.asc())
        .all()
    )
    result = []
    for row in rows:
        for dish in json_loads(row.dishes, []):
            result.append(
                {
                    "name": dish.get("name"),
                    "type": dish.get("type", ""),
                    "date": row.date.isoformat(),
                    "meal": row.meal,
                    "meal_label": MEAL_LABELS.get(row.meal, row.meal),
                }
            )
    return result


def _open_state(settings: dict, start: date) -> dict:
    first, last = _voting_window(settings)
    if not settings.get("vote_enabled", True):
        return {"open": False, "reason": "投票功能已关闭"}
    if start < first:
        return {"open": False, "reason": "该周投票已结束"}
    if start > last:
        return {"open": False, "reason": "该周投票尚未开始"}
    return {"open": True, "reason": ""}


def _week_votes(db: Session, start: date) -> list[Vote]:
    return db.query(Vote).filter(Vote.week_start == start).all()


def _vote_summary(rows: list[Vote]) -> dict:
    """多选投票的统计口径：total_votes 为投票人数，每道菜的 percent 为「选它的人数占比」。"""
    counter = Counter(row.dish_name for row in rows)
    voters = len({row.user_id for row in rows})
    return {
        "counter": counter,
        "voters": voters,
        "picks": len(rows),
        "ranking": [
            {
                "rank": idx + 1,
                "dish_name": name,
                "votes": count,
                "percent": round(count / voters * 100, 1) if voters else 0,
            }
            for idx, (name, count) in enumerate(counter.most_common())
        ],
    }


@router.get("/options")
def options(
    week_start: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = all_settings(db)
    start, end = _week_bounds(week_start or today())
    state = _open_state(settings, start)
    dishes = _week_dishes(db, start)
    mine = (
        db.query(Vote)
        .filter(Vote.user_id == user.id, Vote.week_start == start)
        .order_by(Vote.id.asc())
        .all()
    )
    rows = _week_votes(db, start)
    summary = _vote_summary(rows)
    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        if d.weekday() >= 5:  # 周末不供餐，投票分组只列工作日
            continue
        meals = []
        for meal in ("breakfast", "lunch", "dinner"):
            names = [dish["name"] for dish in dishes if dish["date"] == d.isoformat() and dish["meal"] == meal]
            meals.append({"meal": meal, "label": MEAL_LABELS[meal], "dishes": names})
        days.append({"date": d.isoformat(), "weekday": d.weekday(), "meals": meals})
    unique: dict[str, dict] = {}
    for dish in dishes:
        entry = unique.setdefault(dish["name"], {"name": dish["name"], "type": dish["type"], "dates": []})
        entry["dates"].append({"date": dish["date"], "meal": dish["meal"], "meal_label": dish["meal_label"]})
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        **state,
        "my_votes": [row.dish_name for row in mine],
        "my_vote": vote_out(mine[0]) if mine else None,
        "total_votes": summary["voters"],
        "total_picks": summary["picks"],
        "days": days,
        "dishes": list(unique.values()),
    }


@router.post("")
def submit_vote(
    payload: VoteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = all_settings(db)
    start = week_start_of(payload.week_start)
    state = _open_state(settings, start)
    if not state["open"]:
        raise HTTPException(status_code=400, detail=state["reason"])
    if payload.week_start != start:
        raise HTTPException(status_code=400, detail="week_start 必须是周一")

    names = payload.resolved_names()
    if len(names) > 10:
        raise HTTPException(status_code=400, detail="最多可以投 10 道菜")
    available = {dish["name"] for dish in _week_dishes(db, start)}
    unknown = [name for name in names if name not in available]
    if unknown:
        raise HTTPException(status_code=400, detail=f"该菜品不在此周菜单中：{unknown[0]}")

    existing = (
        db.query(Vote).filter(Vote.user_id == user.id, Vote.week_start == start).all()
    )
    had = bool(existing)
    keep = set(names)
    for row in existing:
        if row.dish_name not in keep:
            db.delete(row)
    current = {row.dish_name for row in existing if row.dish_name in keep}
    for name in names:
        if name not in current:
            db.add(Vote(user_id=user.id, week_start=start, dish_name=name))
    db.commit()

    mine = (
        db.query(Vote)
        .filter(Vote.user_id == user.id, Vote.week_start == start)
        .order_by(Vote.id.asc())
        .all()
    )
    if not names:
        message = "已清空本周投票"
    elif had:
        message = "投票已更新"
    else:
        message = "投票成功，感谢参与"
    return {"message": message, "my_votes": [row.dish_name for row in mine]}


@router.get("/results")
def results(
    week_start: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start, end = _week_bounds(week_start or today())
    settings = all_settings(db)
    state = _open_state(settings, start)
    summary = _vote_summary(_week_votes(db, start))
    mine = (
        db.query(Vote)
        .filter(Vote.user_id == user.id, Vote.week_start == start)
        .order_by(Vote.id.asc())
        .all()
    )
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "total_votes": summary["voters"],
        "total_picks": summary["picks"],
        "ranking": summary["ranking"],
        "my_votes": [row.dish_name for row in mine],
        "my_vote": vote_out(mine[0]) if mine else None,
        "voting_open": state["open"],
        "reason": state["reason"],
    }


@router.get("/stats")
def vote_stats(
    week_start: date | None = None,
    start: date | None = None,
    end: date | None = None,
    days: int = 7,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """投票统计：按周（week_start）或按任意日期区间（start/end）。

    区间口径：Menu 的菜必须在区间内上过，Vote.week_start 落在区间内。
    """
    if start or end:
        end = end or today()
        start = start or end - timedelta(days=max(1, min(days, 365)) - 1)
        if end < start:
            raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
        if (end - start).days > 365:
            raise HTTPException(status_code=400, detail="统计区间不能超过一年")
        week_votes = db.query(Vote).filter(Vote.week_start >= start, Vote.week_start <= end).all()
        eligible = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        summary = _vote_summary(week_votes)
        return {
            "mode": "range",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "total_votes": summary["voters"],
            "total_picks": summary["picks"],
            "eligible": eligible,
            "participation": round(summary["voters"] / eligible * 100, 1) if eligible else 0,
            "ranking": summary["ranking"],
        }

    start, end = _week_bounds(week_start or today())
    summary = _vote_summary(_week_votes(db, start))
    eligible = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    return {
        "mode": "week",
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "total_votes": summary["voters"],
        "total_picks": summary["picks"],
        "eligible": eligible,
        "participation": round(summary["voters"] / eligible * 100, 1) if eligible else 0,
        "ranking": summary["ranking"],
    }


@router.get("/weeks")
def vote_weeks(
    _: User = Depends(get_any_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Menu.date).distinct().all()
    weeks = sorted({week_start_of(row[0]).isoformat() for row in rows})
    current = week_start_of(today()).isoformat()
    if current not in weeks:
        weeks.append(current)
        weeks.sort()
    return {"weeks": weeks, "current": current}
