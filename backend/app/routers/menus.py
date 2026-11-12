from __future__ import annotations

import io
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import MEAL_LABELS, MEALS
from ..database import get_db
from ..deps import get_any_user, require_staff
from ..models import DishTag, Menu, User
from ..schemas import MenuIn
from ..serializers import menu_out
from ..utils import json_dumps, json_loads, local_now, parse_date, week_start_of

router = APIRouter(prefix="/api/menus", tags=["menus"])


# ---------------------------------------------------------------- 菜品类型标签

# 首次使用的默认标签（真正的增删走 /dish-tags 接口）
DEFAULT_DISH_TAGS = ["主食", "荤菜", "素菜", "汤品", "小菜", "凉菜", "其他"]


def _ensure_default_tags(db: Session) -> None:
    if db.query(DishTag).count() == 0:
        db.add_all([DishTag(name=name) for name in DEFAULT_DISH_TAGS])
        db.commit()


@router.get("/dish-tags")
def list_dish_tags(_: User = Depends(get_any_user), db: Session = Depends(get_db)):
    """菜品类型标签列表（无分页，量很小）。"""
    _ensure_default_tags(db)
    rows = db.query(DishTag).order_by(DishTag.id.asc()).all()
    return [{"id": row.id, "name": row.name} for row in rows]


@router.post("/dish-tags")
def create_dish_tag(
    payload: dict,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """新增标签：添加菜品时直接回车创建。重复创建视为成功（幂等）。"""
    name = str((payload or {}).get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="标签名不能为空")
    if len(name) > 20:
        raise HTTPException(status_code=400, detail="标签最多 20 个字")
    row = db.query(DishTag).filter(func.lower(DishTag.name) == name.lower()).first()
    if row:
        return {"id": row.id, "name": row.name, "created": False}
    row = DishTag(name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "created": True}


@router.delete("/dish-tags/{tag_id}")
def delete_dish_tag(
    tag_id: int,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """删除标签。只影响之后的选择列表，已有菜单里的文字不受影响。"""
    row = db.get(DishTag, tag_id)
    if row is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    db.delete(row)
    db.commit()
    return {"message": "标签已删除", "note": "已有菜单不受影响"}


def _range(start: date, end: date) -> list[date]:
    if end < start:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if (end - start).days > 62:
        raise HTTPException(status_code=400, detail="查询范围不能超过 62 天")
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


@router.get("")
def list_menus(
    start: date,
    end: date,
    _: User = Depends(get_any_user),
    db: Session = Depends(get_db),
):
    days = _range(start, end)
    rows = db.query(Menu).filter(Menu.date >= start, Menu.date <= end).all()
    by_key = {(r.date, r.meal): r for r in rows}
    return [
        {
            "date": d.isoformat(),
            "meals": {meal: menu_out(by_key.get((d, meal)), d, meal) for meal in MEALS},
        }
        for d in days
    ]


@router.get("/week")
def week_menus(
    week_start: str | None = None,
    _: User = Depends(get_any_user),
    db: Session = Depends(get_db),
):
    start = week_start_of(parse_date(week_start)) if week_start else week_start_of(local_now().date())
    end = start + timedelta(days=6)
    rows = db.query(Menu).filter(Menu.date >= start, Menu.date <= end).all()
    by_key = {(r.date, r.meal): r for r in rows}
    return {
        "week_start": start.isoformat(),
        "days": [
            {
                "date": d.isoformat(),
                "weekday": d.weekday(),
                "meals": {meal: menu_out(by_key.get((d, meal)), d, meal) for meal in MEALS},
            }
            for d in (start + timedelta(days=i) for i in range(7))
        ],
    }


@router.get("/day/{day}")
def day_menus(day: date, _: User = Depends(get_any_user), db: Session = Depends(get_db)):
    rows = db.query(Menu).filter(Menu.date == day).all()
    by_meal = {r.meal: r for r in rows}
    return {"date": day.isoformat(), "meals": {meal: menu_out(by_meal.get(meal), day, meal) for meal in MEALS}}


@router.put("/{day}/{meal}")
def upsert_menu(
    day: date,
    meal: str,
    payload: MenuIn,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    if meal not in MEALS:
        raise HTTPException(status_code=400, detail="餐次不正确")
    dishes = [
        {"name": item.name.strip()[:60], "type": _normalize_type(item.type)}
        for item in payload.dishes
        if item.name.strip()
    ]
    if not dishes:
        raise HTTPException(status_code=400, detail="至少填写一道菜")
    menu = db.query(Menu).filter(Menu.date == day, Menu.meal == meal).first()
    if menu is None:
        menu = Menu(date=day, meal=meal)
        db.add(menu)
    menu.dishes = json_dumps(dishes)
    menu.note = payload.note.strip()
    menu.updated_by = user.id
    db.commit()
    db.refresh(menu)
    return menu_out(menu)


@router.delete("/{day}/{meal}")
def delete_menu(
    day: date,
    meal: str,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    menu = db.query(Menu).filter(Menu.date == day, Menu.meal == meal).first()
    if menu:
        db.delete(menu)
        db.commit()
    return {"message": "已清空"}


@router.post("/copy")
def copy_week(
    from_week: date,
    to_week: date,
    overwrite: bool = Query(False),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    source_start = week_start_of(from_week)
    target_start = week_start_of(to_week)
    if source_start == target_start:
        raise HTTPException(status_code=400, detail="源周与目标周不能相同")
    sources = (
        db.query(Menu)
        .filter(Menu.date >= source_start, Menu.date <= source_start + timedelta(days=6))
        .all()
    )
    copied = skipped = 0
    for source in sources:
        target_date = target_start + timedelta(days=(source.date - source_start).days)
        existing = db.query(Menu).filter(Menu.date == target_date, Menu.meal == source.meal).first()
        if existing and not overwrite:
            skipped += 1
            continue
        if existing:
            existing.dishes = source.dishes
            existing.note = source.note
        else:
            db.add(Menu(date=target_date, meal=source.meal, dishes=source.dishes, note=source.note))
        copied += 1
    db.commit()
    return {"copied": copied, "skipped": skipped, "to_week": target_start.isoformat()}


@router.get("/dish-options")
def dish_options(
    week_start: date,
    _: User = Depends(get_any_user),
    db: Session = Depends(get_db),
):
    """本周菜单中的所有菜品，按日期/餐次分组，供投票选择。"""
    start = week_start_of(week_start)
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
                }
            )
    return result


# ---------------------------------------------------------------- 模板与导入

DISH_TYPES = ["主食", "荤菜", "素菜", "汤品", "小菜", "凉菜", "其他"]
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
# 与《菜单模板_2026-11-09.xlsx》一致：早餐 5 个空位、午餐 6 个、晚餐 5 个。
TEMPLATE_SLOTS = {"breakfast": 5, "lunch": 6, "dinner": 5}

HEADER_FILL = PatternFill("solid", fgColor="1F6FEB")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
BODY_FONT = Font(color="1F2937", size=10.5)
DAY_FILL = PatternFill("solid", fgColor="F8FAFC")
MEAL_FILLS = {
    "breakfast": PatternFill("solid", fgColor="FFF8EC"),
    "lunch": PatternFill("solid", fgColor="F2FBF5"),
    "dinner": PatternFill("solid", fgColor="F5F3FF"),
}
GRID = Side(style="thin", color="DCE3EC")
CELL_BORDER = Border(left=GRID, right=GRID, top=GRID, bottom=GRID)

MEAL_ALIASES = {
    "早餐": "breakfast",
    "早饭": "breakfast",
    "早点": "breakfast",
    "早": "breakfast",
    "breakfast": "breakfast",
    "午餐": "lunch",
    "中餐": "lunch",
    "午饭": "lunch",
    "中午": "lunch",
    "lunch": "lunch",
    "晚餐": "dinner",
    "晚饭": "dinner",
    "晚": "dinner",
    "dinner": "dinner",
}


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _parse_day(value) -> date | None:
    """兼容 2026-11-09 / 2026/11/9 / 2026年11月9日 / Excel 日期格式。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.split(" ")[0].split("T")[0]
    match = re.search(r"(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})", text)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _normalize_meal(value) -> str | None:
    text = _cell_text(value).lower()
    if not text:
        return None
    return MEAL_ALIASES.get(text)


def _normalize_type(value) -> str:
    """菜品类型：留空按「其他」，已知类型原样，自定义类型（手工输入）也原样保留。"""
    text = _cell_text(value)
    if not text:
        return "其他"
    if text in DISH_TYPES:
        return text
    for dish_type in DISH_TYPES:
        if dish_type in text:
            return dish_type
    return text[:20]


def _style_sheet(ws, widths: list[int], header_height: int = 26) -> None:
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = header_height
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"


@router.get("/template")
def menu_template(
    week_start: str | None = None,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """下载菜单导入模板。

    结构完全对齐用户给的示例：日期/星期按天纵向合并、餐次按餐纵向合并，
    早餐留 5 行、午餐 6 行、晚餐 5 行；已有菜单会预填，菜多的餐自动加行。
    手动插入的行同样能被导入逻辑读取（合并单元格只在首行有值，导入时向下沿用）。
    """
    start = week_start_of(parse_date(week_start)) if week_start else week_start_of(local_now().date())
    rows = db.query(Menu).filter(Menu.date >= start, Menu.date <= start + timedelta(days=6)).all()
    by_key = {(row.date, row.meal): row for row in rows}

    wb = Workbook()
    ws = wb.active
    ws.title = "菜单"
    ws.append(["日期", "星期", "餐次", "菜品名称", "菜品类型"])
    _style_sheet(ws, [13, 8, 10, 26, 12])

    cursor = 2
    for offset in range(7):
        day = start + timedelta(days=offset)
        if day.weekday() >= 5:  # 周末不供餐
            continue
        day_first = cursor
        for meal in MEALS:
            menu = by_key.get((day, meal))
            dishes = json_loads(menu.dishes, []) if menu else []
            dish_count = max(TEMPLATE_SLOTS[meal], len(dishes))
            meal_first = cursor
            for slot in range(dish_count):
                dish = dishes[slot] if slot < len(dishes) else None
                ws.cell(row=cursor, column=1, value=day.isoformat())
                ws.cell(row=cursor, column=2, value=WEEKDAYS[day.weekday()])
                ws.cell(row=cursor, column=3, value=MEAL_LABELS[meal])
                ws.cell(row=cursor, column=4, value=(dish or {}).get("name", ""))
                ws.cell(row=cursor, column=5, value=_normalize_type((dish or {}).get("type")) if dish else "")
                for col in range(1, 6):
                    cell = ws.cell(row=cursor, column=col)
                    cell.border = CELL_BORDER
                    cell.font = BODY_FONT
                    cell.alignment = Alignment(
                        horizontal="left" if col == 4 else "center",
                        vertical="center",
                    )
                ws.row_dimensions[cursor].height = 22
                cursor += 1
            ws.merge_cells(start_row=meal_first, start_column=3, end_row=cursor - 1, end_column=3)
            ws.cell(row=meal_first, column=3).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=meal_first, column=3).fill = MEAL_FILLS[meal]
        ws.merge_cells(start_row=day_first, start_column=1, end_row=cursor - 1, end_column=1)
        ws.merge_cells(start_row=day_first, start_column=2, end_row=cursor - 1, end_column=2)
        for col in (1, 2):
            cell = ws.cell(row=day_first, column=col)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = DAY_FILL
            cell.font = Font(color="0F172A", size=10.5, bold=col == 1)

    tip = wb.create_sheet("填写说明")
    for line in (
        ["项目", "说明"],
        ["日期", "必填，格式 2026-11-16（2026/11/16、2026年11月16日 也可以）"],
        ["餐次", "必填，三种之一：早餐、午餐、晚餐"],
        ["菜品名称", "必填，一道菜一行；早餐、晚餐各留 5 行，午餐留 6 行"],
        ["菜品类型", f"可选，{'、'.join(DISH_TYPES)}；留空按「其他」处理"],
        ["加一行菜", "模板里的空行可以直接填；菜多时在该餐中间插入行继续写，导入时会按上下顺序读取"],
        ["整行空白", "空行会被自动跳过，不影响导入"],
        ["周末", "周六日不供餐，模板中不出现，导入时也会跳过"],
        ["导入规则", "同一天同一餐的多行会整体替换该餐原有菜单"],
    ):
        tip.append(line)
    _style_sheet(tip, [14, 64], header_height=24)
    for row in tip.iter_rows(min_row=2, max_row=tip.max_row):
        for cell in row:
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.font = BODY_FONT

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"菜单模板_{start}.xlsx"
    ascii_name = f"menu_template_{start}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename={ascii_name}; filename*=UTF-8''{quote(filename)}"
            )
        },
    )


@router.post("/import")
async def import_menus(
    file: UploadFile = File(...),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """按模板批量导入菜单。

    读取规则（兼容手动改过的表格）：
      * 日期 / 餐次 纵向合并时只有首行有值 —— 向下沿用；
      * 手动插入的行只要填了菜名，就归到当前日期 + 当前餐次；
      * 空行、空菜名直接跳过；周末行跳过并计数。
    """
    filename = (file.filename or "").lower()
    if not filename.endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 格式的 Excel 文件")

    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - 任何解析失败都提示格式问题
        raise HTTPException(status_code=400, detail="Excel 解析失败，请使用下载的模板填写") from None

    ws = wb["菜单"] if "菜单" in wb.sheetnames else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="表格是空的")

    header = [_cell_text(cell).replace(" ", "") for cell in rows[0]]

    def column(*names: str) -> int | None:
        for idx, title in enumerate(header):
            if title in names:
                return idx
        for idx, title in enumerate(header):
            if any(name and name in title for name in names):
                return idx
        return None

    col_date = column("日期", "date")
    col_meal = column("餐次", "meal")
    col_name = column("菜品名称", "菜名", "name", "dish")
    col_type = column("菜品类型", "类型", "type")
    if col_date is None or col_meal is None or col_name is None:
        raise HTTPException(
            status_code=400,
            detail="表头不完整，需要「日期 / 餐次 / 菜品名称」三列，请下载最新模板填写",
        )

    grouped: dict[tuple[date, str], list[dict]] = {}
    failed: list[dict] = []
    skipped_weekend = 0
    last_day: date | None = None
    last_meal: str | None = None

    for index, row in enumerate(rows[1:], start=2):
        cells = list(row) + [None] * 8
        if not any(_cell_text(cell) for cell in cells[: max(col_name + 1, col_date + 1, col_meal + 1)]):
            continue  # 整行空白

        if _cell_text(cells[col_date]):
            parsed = _parse_day(cells[col_date])
            if parsed is None:
                failed.append({"row": index, "reason": f"日期无法识别：{_cell_text(cells[col_date])}"})
                last_day = None
            else:
                last_day = parsed
        if _cell_text(cells[col_meal]):
            parsed_meal = _normalize_meal(cells[col_meal])
            if parsed_meal is None:
                failed.append({"row": index, "reason": f"餐次无法识别：{_cell_text(cells[col_meal])}"})
            last_meal = parsed_meal

        name = _cell_text(cells[col_name])
        if not name:
            continue  # 模板预留的空位
        if last_day is None or last_meal is None:
            failed.append({"row": index, "reason": "无法确定所属日期或餐次，请检查合并单元格"})
            continue
        if last_day.weekday() >= 5:
            skipped_weekend += 1
            continue
        grouped.setdefault((last_day, last_meal), []).append(
            {"name": name[:60], "type": _normalize_type(cells[col_type] if col_type is not None else None)}
        )

    if not grouped:
        detail = "；".join(f"第{item['row']}行 {item['reason']}" for item in failed[:3]) or "没有可导入的数据"
        raise HTTPException(status_code=400, detail=f"没有可导入的菜单：{detail}")

    menus = dishes = 0
    for (day, meal) in sorted(grouped):
        items = grouped[(day, meal)]
        menu = db.query(Menu).filter(Menu.date == day, Menu.meal == meal).first()
        if menu is None:
            menu = Menu(date=day, meal=meal)
            db.add(menu)
        menu.dishes = json_dumps(items)
        menu.updated_by = user.id
        menus += 1
        dishes += len(items)
    db.commit()

    return {
        "menus": menus,
        "dishes": dishes,
        "days": len({day for day, _ in grouped}),
        "failed": failed,
        "skipped_weekend": skipped_weekend,
        "start": min(day for day, _ in grouped).isoformat(),
        "end": max(day for day, _ in grouped).isoformat(),
    }
