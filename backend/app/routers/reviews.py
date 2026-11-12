from __future__ import annotations

import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import MEALS
from ..database import get_db
from ..deps import get_current_user, require_staff
from ..models import Menu, Review, User
from ..schemas import ReviewIn
from ..serializers import review_out
from ..utils import json_loads, today, week_start_of

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

RATING_LABELS = {5: "非常好", 4: "很好", 3: "良好", 2: "一般", 1: "很差"}
MEAL_LABELS = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}


@router.get("/mine")
def my_reviews_of_day(
    day: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当天三餐各自的评价（可只评其中一餐）。"""
    day = day or today()
    rows = db.query(Review).filter(Review.user_id == user.id, Review.date == day).all()
    by_meal = {meal: None for meal in MEALS}
    for row in rows:
        by_meal[row.meal] = {**review_out(row), "rating_label": RATING_LABELS.get(row.rating, "")}
    return by_meal


@router.get("/history")
def my_reviews(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Review)
        .filter(Review.user_id == user.id)
        .order_by(Review.date.desc(), Review.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            **review_out(r),
            "rating_label": RATING_LABELS.get(r.rating, ""),
            "meal_label": MEAL_LABELS.get(r.meal, ""),
        }
        for r in rows
    ]


@router.post("")
def submit_review(
    payload: ReviewIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.date > today():
        raise HTTPException(status_code=400, detail="不能评价未来的餐次")
    if payload.meal not in MEALS:
        raise HTTPException(status_code=400, detail="餐次不正确")
    if payload.rating >= 3:
        payload = payload.model_copy(update={"taste": "", "pairing": "", "portion": ""})
    elif payload.rating <= 2 and not (payload.taste or payload.pairing or payload.portion or payload.comment.strip()):
        raise HTTPException(status_code=400, detail="评分较低时，请补充至少一项原因，帮助我们改进")
    row = (
        db.query(Review)
        .filter(Review.user_id == user.id, Review.date == payload.date, Review.meal == payload.meal)
        .first()
    )
    if row is None:
        row = Review(user_id=user.id, date=payload.date, meal=payload.meal)
        db.add(row)
    row.rating = payload.rating
    row.taste = payload.taste
    row.pairing = payload.pairing
    row.portion = payload.portion
    row.comment = payload.comment.strip()
    db.commit()
    return {"message": "评价已提交，感谢你的真实反馈", "review": review_out(row)}


@router.get("/summary")
def review_summary(
    start: date | None = None,
    end: date | None = None,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    end = end or week_start_of(today()) + timedelta(days=6)
    start = start or week_start_of(today())
    rows = db.query(Review).filter(Review.date >= start, Review.date <= end).all()
    total = len(rows)
    distribution = {str(i): 0 for i in range(1, 6)}
    taste: dict[str, int] = {}
    pairing: dict[str, int] = {}
    portion: dict[str, int] = {}
    by_day: dict[str, list[int]] = {}
    for row in rows:
        distribution[str(row.rating)] = distribution.get(str(row.rating), 0) + 1
        if row.taste:
            taste[row.taste] = taste.get(row.taste, 0) + 1
        if row.pairing:
            pairing[row.pairing] = pairing.get(row.pairing, 0) + 1
        if row.portion:
            portion[row.portion] = portion.get(row.portion, 0) + 1
        by_day.setdefault(row.date.isoformat(), []).append(row.rating)
    series = []
    for i in range((end - start).days + 1):
        d = (start + timedelta(days=i)).isoformat()
        scores = by_day.get(d, [])
        series.append(
            {
                "date": d,
                "count": len(scores),
                "avg": round(sum(scores) / len(scores), 2) if scores else None,
                "low": sum(1 for score in scores if score <= 2),
                "good": sum(1 for score in scores if score >= 4),
            }
        )
    avg = round(sum(r.rating for r in rows) / total, 2) if total else 0
    good = sum(1 for r in rows if r.rating >= 3)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total": total,
        "avg": avg,
        "good_rate": round(good / total * 100, 1) if total else 0,
        "distribution": [{"rating": i, "label": RATING_LABELS[i], "count": distribution[str(i)]} for i in range(5, 0, -1)],
        "reasons": {
            "taste": [{"label": k, "count": v} for k, v in sorted(taste.items(), key=lambda x: -x[1])],
            "pairing": [{"label": k, "count": v} for k, v in sorted(pairing.items(), key=lambda x: -x[1])],
            "portion": [{"label": k, "count": v} for k, v in sorted(portion.items(), key=lambda x: -x[1])],
        },
        "series": series,
    }


@router.get("/day/{day}")
def review_day(day: date, _: User = Depends(require_staff), db: Session = Depends(get_db)):
    """某一天的评价详情：按早/中/晚拆分，并带上当天这三餐的菜单（匿名，不含员工信息）。"""
    reviews = db.query(Review).filter(Review.date == day).all()
    menus = db.query(Menu).filter(Menu.date == day).all()
    dishes = {row.meal: json_loads(row.dishes, []) for row in menus}

    meals = {}
    for meal in MEALS:
        rows = sorted(
            (row for row in reviews if row.meal == meal),
            key=lambda row: (row.rating, row.created_at or row.date),
        )
        count = len(rows)
        meals[meal] = {
            "meal": meal,
            "label": MEAL_LABELS.get(meal, meal),
            "count": count,
            "avg": round(sum(row.rating for row in rows) / count, 2) if count else None,
            "low": sum(1 for row in rows if row.rating <= 2),
            "distribution": [
                {
                    "rating": rating,
                    "label": RATING_LABELS[rating],
                    "count": sum(1 for row in rows if row.rating == rating),
                }
                for rating in (5, 4, 3, 2, 1)
            ],
            "comments": [
                {
                    "id": row.id,
                    "rating": row.rating,
                    "rating_label": RATING_LABELS.get(row.rating, ""),
                    "comment": row.comment,
                    "taste": row.taste,
                    "pairing": row.pairing,
                    "portion": row.portion,
                    "created_at": row.created_at.isoformat(timespec="minutes") if row.created_at else None,
                }
                for row in rows
            ],
            "dishes": dishes.get(meal, []),
        }

    total = len(reviews)
    return {
        "date": day.isoformat(),
        "weekday": day.weekday(),
        "total": total,
        "avg": round(sum(row.rating for row in reviews) / total, 2) if total else None,
        "meals": meals,
    }


@router.get("/recent")
def recent_reviews(
    limit: int = Query(10, ge=1, le=50),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    rows = db.query(Review).order_by(Review.created_at.desc()).limit(limit).all()
    # 匿名：不返回用户信息
    return [
        {
            **review_out(r),
            "rating_label": RATING_LABELS.get(r.rating, ""),
        }
        for r in rows
    ]


# ---------------------------------------------------------------- 导出

HEADER_FILL = PatternFill("solid", fgColor="1F6FEB")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _style_header(ws, widths: list[int]) -> None:
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    for idx, width in enumerate(widths):
        ws.column_dimensions[chr(65 + idx)].width = width


def _split(row: Review, field: str) -> list[str]:
    """评价原因字段可能存多个（逗号分隔），导出时拆成列表。"""
    raw = getattr(row, field, "") or ""
    return [item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()]


@router.get("/export")
def export_reviews(
    start: date,
    end: date,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """按日期区间导出菜品评价（匿名：不含姓名与手机号）。"""
    if end < start:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if (end - start).days > 366:
        raise HTTPException(status_code=400, detail="导出区间不能超过一年")

    rows = (
        db.query(Review)
        .filter(Review.date >= start, Review.date <= end)
        .order_by(Review.date.asc(), Review.meal.asc(), Review.id.asc())
        .all()
    )

    wb = Workbook()

    # 汇总
    ws = wb.active
    ws.title = "每日汇总"
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    ws.append(["日期", "星期", "评价数", "平均分", "好评率(%)", "低分(一般/很差)"])
    _style_header(ws, [14, 8, 10, 10, 12, 16])

    by_day: dict[date, list[Review]] = {}
    for row in rows:
        by_day.setdefault(row.date, []).append(row)

    total = 0
    for i in range((end - start).days + 1):
        day = start + timedelta(days=i)
        items = by_day.get(day, [])
        total += len(items)
        if items:
            avg = sum(item.rating for item in items) / len(items)
            good = sum(1 for item in items if item.rating >= 4)
            low = sum(1 for item in items if item.rating <= 2)
            ws.append(
                [
                    day.isoformat(),
                    weekdays[day.weekday()],
                    len(items),
                    round(avg, 2),
                    round(good / len(items) * 100, 1),
                    low,
                ]
            )
        else:
            ws.append([day.isoformat(), weekdays[day.weekday()], 0, "", "", 0])

    ws.append([])
    if rows:
        avg_all = sum(item.rating for item in rows) / len(rows)
        ws.append(
            [
                "合计",
                "",
                total,
                round(avg_all, 2),
                round(sum(1 for item in rows if item.rating >= 4) / len(rows) * 100, 1),
                sum(1 for item in rows if item.rating <= 2),
            ]
        )
        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)

    # 评分分布
    dist_ws = wb.create_sheet("评分分布")
    dist_ws.append(["评分", "说明", "数量", "占比(%)"])
    _style_header(dist_ws, [10, 12, 10, 10])
    for rating in (5, 4, 3, 2, 1):
        count = sum(1 for item in rows if item.rating == rating)
        dist_ws.append(
            [rating, RATING_LABELS[rating], count, round(count / len(rows) * 100, 1) if rows else 0]
        )

    # 不满意原因（口味 / 搭配 / 分量，按次数排序）
    reason_ws = wb.create_sheet("不满意原因")
    reason_ws.append(["类型", "选项", "次数"])
    _style_header(reason_ws, [12, 24, 10])
    for title, field in (("口味", "taste"), ("搭配", "pairing"), ("分量", "portion")):
        counter: dict[str, int] = {}
        for item in rows:
            for key in _split(item, field):
                counter[key] = counter.get(key, 0) + 1
        if not counter:
            reason_ws.append([title, "（无）", 0])
        for key, count in sorted(counter.items(), key=lambda pair: -pair[1]):
            reason_ws.append([title, key, count])

    # 明细（匿名）
    detail_ws = wb.create_sheet("评价明细")
    detail_ws.append(["日期", "星期", "餐次", "评分", "评价", "口味", "搭配", "分量", "评论"])
    _style_header(detail_ws, [14, 8, 8, 8, 12, 22, 22, 18, 40])
    for item in rows:
        detail_ws.append(
            [
                item.date.isoformat(),
                weekdays[item.date.weekday()],
                MEAL_LABELS.get(item.meal, item.meal),
                item.rating,
                RATING_LABELS.get(item.rating, ""),
                "、".join(_split(item, "taste")),
                "、".join(_split(item, "pairing")),
                "、".join(_split(item, "portion")),
                item.comment,
            ]
        )

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"dish_reviews_{start}_{end}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
