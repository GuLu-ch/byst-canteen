from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import MEALS
from ..database import get_db
from ..deps import get_current_user, require_staff
from ..models import Feedback, Menu, Reservation, Review, User, Vote
from ..utils import all_settings, json_loads, local_now, today, week_start_of

router = APIRouter(prefix="/api/stats", tags=["stats"])

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MEALS_CN = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}


def _counts(db: Session, start: date, end: date) -> dict:
    rows = (
        db.query(Reservation.date, Reservation.meal, func.count(Reservation.id))
        .filter(
            Reservation.date >= start,
            Reservation.date <= end,
            Reservation.status == "reserved",
        )
        .group_by(Reservation.date, Reservation.meal)
        .all()
    )
    return {(r[0], r[1]): r[2] for r in rows}


def _day_block(counts: dict, d: date) -> dict:
    return {
        "date": d.isoformat(),
        "label": WEEKDAYS[d.weekday()],
        "meals": {meal: counts.get((d, meal), 0) for meal in MEALS},
        "total": sum(counts.get((d, meal), 0) for meal in MEALS),
    }


@router.get("/overview")
def overview(
    start: date | None = None,
    end: date | None = None,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """总览：固定区块（今日/明日就餐、菜单完整度）+ 随区间变化的统计（预约/评价/反馈/投票）。

    区间口径与前端「今日 / 本周 / 最近30天」一致，缺省为本周。
    """
    now = local_now()
    today_date = now.date()
    tomorrow = today_date + timedelta(days=1)

    end = end or week_start_of(today_date) + timedelta(days=6)
    start = start or week_start_of(today_date)
    if end < start:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if (end - start).days > 120:
        raise HTTPException(status_code=400, detail="统计区间不能超过 120 天")

    counts = _counts(db, min(start, today_date), max(end, today_date + timedelta(days=13)))

    week_start = week_start_of(today_date)
    week = [_day_block(counts, week_start + timedelta(days=i)) for i in range(7)]

    user_total = db.query(func.count(User.id)).scalar() or 0
    user_active = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0

    # ── 随区间变化的统计 ──
    range_reservations = (
        db.query(func.count(Reservation.id))
        .filter(
            Reservation.date >= start,
            Reservation.date <= end,
            Reservation.status == "reserved",
        )
        .scalar()
        or 0
    )
    reservation_days = db.query(Reservation.date).filter(
        Reservation.date >= start, Reservation.date <= end, Reservation.status == "reserved"
    ).distinct().count() or 1

    feedback_rows = (
        db.query(Feedback).filter(Feedback.date >= start, Feedback.date <= end).all()
    )
    pending_feedback = (
        db.query(func.count(Feedback.id)).filter(Feedback.handled.is_(False)).scalar() or 0
    )

    review_rows = db.query(Review).filter(Review.date >= start, Review.date <= end).all()
    review_count = len(review_rows)
    review_avg = round(sum(r.rating for r in review_rows) / review_count, 2) if review_count else 0
    distribution = {i: 0 for i in range(1, 6)}
    for row in review_rows:
        distribution[row.rating] += 1

    # 区间内被投票的菜（Vote.week_start 落在区间内）
    vote_rows = db.query(Vote).filter(Vote.week_start >= start, Vote.week_start <= end).all()
    vote_counter = Counter(row.dish_name for row in vote_rows)

    menu_dates = {
        (row.date, row.meal)
        for row in db.query(Menu.date, Menu.meal)
        .filter(Menu.date >= today_date, Menu.date <= today_date + timedelta(days=6))
        .all()
    }
    missing = []
    for i in range(7):
        d = today_date + timedelta(days=i)
        if d.weekday() >= 5:  # 周末不供餐，不计入缺口
            continue
        for meal in MEALS:
            if (d, meal) not in menu_dates:
                missing.append({"date": d.isoformat(), "meal": meal, "label": WEEKDAYS[d.weekday()]})

    # 明日菜单（真实内容）：周末或未上传时给出明确状态
    tomorrow_menus = (
        db.query(Menu)
        .filter(Menu.date == tomorrow)
        .order_by(Menu.meal.asc())
        .all()
    )
    tomorrow_by_meal = {row.meal: json_loads(row.dishes, []) for row in tomorrow_menus}
    tomorrow_is_weekend = tomorrow.weekday() >= 5
    tomorrow_ready = (
        not tomorrow_is_weekend and all(meal in tomorrow_by_meal and tomorrow_by_meal[meal] for meal in MEALS)
    )
    tomorrow_menu = {
        "date": tomorrow.isoformat(),
        "weekday": WEEKDAYS[tomorrow.weekday()],
        "is_weekend": tomorrow_is_weekend,
        "ready": tomorrow_ready,
        "meals": [
            {
                "meal": meal,
                "label": MEALS_CN[meal],
                "dishes": tomorrow_by_meal.get(meal, []),
            }
            for meal in MEALS
        ],
    }

    recent_feedback = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(5).all()

    workdays_left = sum(1 for i in range(7) if (today_date + timedelta(days=i)).weekday() < 5)
    total_slots = workdays_left * len(MEALS)

    return {
        "server_time": now.isoformat(timespec="minutes"),
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "today": _day_block(counts, today_date),
        "tomorrow": _day_block(counts, tomorrow),
        "week": {"start": week_start.isoformat(), "end": (week_start + timedelta(days=6)).isoformat(), "days": week},
        "users": {"total": user_total, "active": user_active},
        "feedback": {
            "total_range": len(feedback_rows),
            "pending": pending_feedback,
            "recent": [
                {
                    "id": r.id,
                    "category": r.category,
                    "content": r.content,
                    "date": r.date.isoformat(),
                    "created_at": r.created_at.isoformat(timespec="minutes") if r.created_at else None,
                    "handled": r.handled,
                }
                for r in recent_feedback
            ],
        },
        "reviews": {
            "count_range": review_count,
            "avg_range": review_avg,
            "distribution": [{"rating": i, "count": distribution[i]} for i in range(5, 0, -1)],
        },
        "reservations": {
            "total_range": range_reservations,
            "avg_per_day": round(range_reservations / reservation_days, 1),
            "active_days": reservation_days,
        },
        "votes": {
            "mode": "range",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "total": len(vote_rows),
            "ranking": [
                {"dish_name": name, "votes": count} for name, count in vote_counter.most_common(5)
            ],
        },
        "menus": {
            "complete": max(0, total_slots - len(missing)),
            "total": total_slots,
            "missing": missing[:8],
        },
        "tomorrow_menu": tomorrow_menu,
    }


@router.get("/me")
def my_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today_date = today()
    upcoming = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user.id,
            Reservation.status == "reserved",
            Reservation.date >= today_date,
        )
        .order_by(Reservation.date.asc(), Reservation.meal.asc())
        .all()
    )
    review_count = db.query(func.count(Review.id)).filter(Review.user_id == user.id).scalar() or 0
    vote_count = db.query(func.count(Vote.id)).filter(Vote.user_id == user.id).scalar() or 0
    feedback_count = db.query(func.count(Feedback.id)).filter(Feedback.user_id == user.id).scalar() or 0
    next_item = upcoming[0] if upcoming else None
    return {
        "upcoming_count": len(upcoming),
        "upcoming": [
            {"id": r.id, "date": r.date.isoformat(), "meal": r.meal} for r in upcoming[:10]
        ],
        "next": (
            {"id": next_item.id, "date": next_item.date.isoformat(), "meal": next_item.meal}
            if next_item
            else None
        ),
        "review_count": review_count,
        "vote_count": vote_count,
        "feedback_count": feedback_count,
    }


@router.get("/trend")
def trend(
    days: int = 14,
    start: date | None = None,
    end: date | None = None,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    end = end or today()
    start = start or end - timedelta(days=max(7, min(days, 60)) - 1)
    if end < start:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if (end - start).days > 120:
        raise HTTPException(status_code=400, detail="统计区间不能超过 120 天")
    counts = _counts(db, start, end)
    series = [_day_block(counts, start + timedelta(days=i)) for i in range((end - start).days + 1)]
    return {"start": start.isoformat(), "end": end.isoformat(), "series": series}
