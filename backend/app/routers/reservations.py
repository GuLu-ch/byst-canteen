from __future__ import annotations

import io
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import MEAL_LABELS, MEALS
from ..database import get_db
from ..deps import get_current_user, require_staff
from ..models import Reservation, User
from ..schemas import BulkReservationIn
from ..serializers import reservation_out
from ..utils import all_settings, local_now, reservation_state

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _check_range(start: date, end: date):
    if end < start:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if (end - start).days > 62:
        raise HTTPException(status_code=400, detail="查询范围不能超过 62 天")


@router.get("/availability")
def availability(
    start: date,
    end: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_range(start, end)
    settings = all_settings(db)
    mine = {
        (r.date, r.meal)
        for r in db.query(Reservation)
        .filter(
            Reservation.user_id == user.id,
            Reservation.date >= start,
            Reservation.date <= end,
            Reservation.status == "reserved",
        )
        .all()
    }
    now = local_now()
    days = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        meals = {}
        for meal in MEALS:
            state = reservation_state(settings, meal, d, now)
            state["reserved"] = (d, meal) in mine
            meals[meal] = state
        days.append({"date": d.isoformat(), "weekday": d.weekday(), "meals": meals})
    return {"days": days, "server_time": now.isoformat(timespec="minutes")}


@router.get("/mine")
def my_reservations(
    start: date | None = None,
    end: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Reservation).filter(Reservation.user_id == user.id, Reservation.status == "reserved")
    if start:
        query = query.filter(Reservation.date >= start)
    if end:
        query = query.filter(Reservation.date <= end)
    rows = query.order_by(Reservation.date.asc(), Reservation.meal.asc()).all()
    grouped: dict[str, list] = defaultdict(list)
    for row in rows:
        grouped[row.date.isoformat()].append(reservation_out(row))
    return {
        "items": [reservation_out(r) for r in rows],
        "grouped": [{"date": d, "meals": items} for d, items in grouped.items()],
    }


@router.post("/bulk")
def bulk_reserve(
    payload: BulkReservationIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="请选择要预约的餐次")
    if len(payload.items) > 50:
        raise HTTPException(status_code=400, detail="单次最多预约 50 个餐次")
    settings = all_settings(db)
    now = local_now()
    saved = 0
    skipped: list[dict] = []
    seen: set[tuple[date, str]] = set()
    for item in payload.items:
        key = (item.date, item.meal)
        if item.meal not in MEALS:
            skipped.append({"date": item.date.isoformat(), "meal": item.meal, "reason": "餐次不正确"})
            continue
        if key in seen:
            continue
        seen.add(key)
        state = reservation_state(settings, item.meal, item.date, now)
        if not state["open"]:
            skipped.append({"date": item.date.isoformat(), "meal": item.meal, "reason": state["reason"]})
            continue
        row = (
            db.query(Reservation)
            .filter(Reservation.user_id == user.id, Reservation.date == item.date, Reservation.meal == item.meal)
            .first()
        )
        if row is None:
            db.add(Reservation(user_id=user.id, date=item.date, meal=item.meal, status="reserved"))
        elif row.status != "reserved":
            row.status = "reserved"
            row.updated_at = now
        else:
            skipped.append({"date": item.date.isoformat(), "meal": item.meal, "reason": "已经预约过"})
            continue
        saved += 1
    db.commit()
    return {
        "saved": saved,
        "skipped": skipped,
        "message": f"已预约 {saved} 个餐次" + (f"，{len(skipped)} 个未成功" if skipped else ""),
    }


@router.delete("/{reservation_id}")
def cancel_reservation(
    reservation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Reservation, reservation_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if row.status != "reserved":
        raise HTTPException(status_code=400, detail="该预约已取消")
    settings = all_settings(db)
    state = reservation_state(settings, row.meal, row.date)
    if not state["open"]:
        raise HTTPException(status_code=400, detail=f"无法取消：{state['reason']}")
    row.status = "cancelled"
    db.commit()
    return {"message": "已取消预约"}


@router.get("/summary")
def summary(
    start: date,
    end: date,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    _check_range(start, end)
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
    counts = {(r[0], r[1]): r[2] for r in rows}
    days = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        meals = {meal: counts.get((d, meal), 0) for meal in MEALS}
        days.append({"date": d.isoformat(), "weekday": d.weekday(), "meals": meals, "total": sum(meals.values())})
    return {"days": days, "total": sum(day["total"] for day in days)}


@router.get("/detail")
def detail(
    day: date,
    meal: str,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    if meal not in MEALS:
        raise HTTPException(status_code=400, detail="餐次不正确")
    rows = (
        db.query(Reservation, User)
        .join(User, Reservation.user_id == User.id)
        .filter(Reservation.date == day, Reservation.meal == meal, Reservation.status == "reserved")
        .order_by(User.department.asc(), User.name.asc())
        .all()
    )
    departments: dict[str, int] = defaultdict(int)
    items = []
    for reservation, user in rows:
        departments[user.department or "未分组"] += 1
        items.append(
            {
                "name": user.name,
                "phone": user.phone,
                "department": user.department or "",
                "allergens": user.allergens,
                "preferences": user.preferences,
            }
        )
    return {
        "date": day.isoformat(),
        "meal": meal,
        "total": len(items),
        "items": items,
        "departments": [{"name": k, "count": v} for k, v in sorted(departments.items(), key=lambda x: -x[1])],
    }


@router.get("/export")
def export(
    start: date,
    end: date,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    _check_range(start, end)
    wb = Workbook()
    ws = wb.active
    ws.title = "预约汇总"
    header_fill = PatternFill("solid", fgColor="E86A33")
    header_font = Font(color="FFFFFF", bold=True)
    headers = ["日期", "星期", "早餐", "午餐", "晚餐", "合计"]
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

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
    counts = {(r[0], r[1]): r[2] for r in rows}
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    grand = 0
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        values = [counts.get((d, meal), 0) for meal in MEALS]
        grand += sum(values)
        ws.append([d.isoformat(), weekdays[d.weekday()], *values, sum(values)])
    ws.append(["合计", "", *[sum(counts.get((start + timedelta(days=i), m), 0) for i in range((end - start).days + 1)) for m in MEALS], grand])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(horizontal="center")
    for idx, width in enumerate([14, 10, 10, 10, 10, 10]):
        ws.column_dimensions[chr(65 + idx)].width = width

    detail_ws = wb.create_sheet("预约明细")
    detail_ws.append(["日期", "餐次", "姓名", "手机号", "部门", "忌口", "偏好"])
    for cell in detail_ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    details = (
        db.query(Reservation, User)
        .join(User, Reservation.user_id == User.id)
        .filter(
            Reservation.date >= start,
            Reservation.date <= end,
            Reservation.status == "reserved",
        )
        .order_by(Reservation.date.asc(), Reservation.meal.asc(), User.name.asc())
        .all()
    )
    for reservation, user in details:
        detail_ws.append(
            [
                reservation.date.isoformat(),
                MEAL_LABELS[reservation.meal],
                user.name,
                user.phone,
                user.department,
                user.allergens,
                user.preferences,
            ]
        )
    for idx, width in enumerate([14, 10, 12, 16, 16, 20, 24]):
        detail_ws.column_dimensions[chr(65 + idx)].width = width

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"meal_reservations_{start}_{end}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
