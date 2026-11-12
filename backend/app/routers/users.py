from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..config import ROLE_LABELS, ROLES
from ..database import get_db
from ..deps import require_admin
from ..models import Reservation, User
from ..schemas import UserIn, UserUpdateIn
from ..serializers import user_out
from ..utils import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])

DEFAULT_PASSWORD = "123456"
STAFF_ROLES = ("admin", "cook")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,20}$")


def clean_username(value: str | None) -> str | None:
    """管理端登录账号：3-20 位字母/数字/下划线/点/中划线，空值表示不设置。"""
    text = (value or "").strip()
    if not text:
        return None
    if not USERNAME_RE.match(text):
        raise HTTPException(status_code=400, detail="账号需为 3-20 位字母、数字或 _ . - 组合")
    return text


def assert_username_free(db: Session, username: str, exclude_id: int | None = None) -> None:
    query = db.query(User).filter(func.lower(User.username) == username.lower())
    if exclude_id:
        query = query.filter(User.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"账号 {username} 已被占用")


def role_from_text(value: str) -> str:
    text = (value or "").strip()
    if text in ROLES:
        return text
    for key, label in ROLE_LABELS.items():
        if text == label:
            return key
    return "employee"


@router.get("")
def list_users(
    q: str = "",
    role: str = "",
    active: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.name.like(like),
                User.phone.like(like),
                User.department.like(like),
                User.username.like(like),
            )
        )
    if role:
        query = query.filter(User.role == role)
    if active in ("true", "false"):
        query = query.filter(User.is_active.is_(active == "true"))
    total = query.count()
    items = query.order_by(User.role.desc(), User.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size, "items": [user_out(u) for u in items]}


@router.get("/overview")
def users_overview(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    active = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    return {"total": sum(r[1] for r in rows), "active": active, "by_role": {r[0]: r[1] for r in rows}}


@router.post("")
def create_user(payload: UserIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    if not re.match(r"^\d{5,20}$", phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="角色不正确")
    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="该手机号已存在")
    username = clean_username(payload.username)
    if payload.role in STAFF_ROLES:
        if not username:
            raise HTTPException(status_code=400, detail="管理员/厨师需要设置登录账号")
        assert_username_free(db, username)
    else:
        username = None
    user = User(
        phone=phone,
        username=username,
        name=payload.name.strip(),
        role=payload.role,
        department=payload.department.strip(),
        password_hash=hash_password(payload.password or DEFAULT_PASSWORD),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in ROLES:
        raise HTTPException(status_code=400, detail="角色不正确")
    if user.id == admin.id and data.get("is_active") is False:
        raise HTTPException(status_code=400, detail="不能停用自己的账号")
    if user.id == admin.id and data.get("role") and data["role"] != "admin":
        raise HTTPException(status_code=400, detail="不能修改自己的管理员角色")
    if "password" in data and data["password"]:
        if len(data["password"]) < 6:
            raise HTTPException(status_code=400, detail="密码至少 6 位")
        user.password_hash = hash_password(data["password"])
    target_role = data.get("role") or user.role
    if "username" in data:
        username = clean_username(data["username"])
        if target_role in STAFF_ROLES:
            if not username:
                raise HTTPException(status_code=400, detail="管理员/厨师需要设置登录账号")
            assert_username_free(db, username, exclude_id=user.id)
            user.username = username
        else:
            user.username = None
    elif target_role not in STAFF_ROLES:
        user.username = None
    elif not user.username and target_role in STAFF_ROLES and "role" in data:
        raise HTTPException(status_code=400, detail="改为管理员/厨师时需要设置登录账号")
    for key in ("name", "role", "department", "is_active"):
        if key in data and data[key] is not None:
            setattr(user, key, data[key])
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    user.password_hash = hash_password(DEFAULT_PASSWORD)
    db.commit()
    return {"message": f"密码已重置为 {DEFAULT_PASSWORD}"}


@router.delete("/{user_id}")
def disable_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能停用自己的账号")
    user.is_active = False
    db.commit()
    return {"message": "账号已停用"}


@router.get("/template")
def download_template(_: User = Depends(require_admin)):
    wb = Workbook()
    ws = wb.active
    ws.title = "员工导入模板"
    ws.append(["姓名", "手机号", "部门", "角色", "账号", "初始密码"])
    ws.append(["张三", "13800000001", "技术部", "员工", "", "123456"])
    ws.append(["李师傅", "13800000002", "食堂", "厨师", "chef_li", "123456"])
    widths = [14, 18, 16, 12, 16, 14]
    for idx, width in enumerate(widths):
        ws.column_dimensions[chr(65 + idx)].width = width
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=employee_template.xlsx"},
    )


def _read_rows(filename: str, content: bytes) -> list[list[str]]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        return [[c.strip() for c in row] for row in csv.reader(io.StringIO(text))]
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append(["" if cell is None else str(cell).strip() for cell in row])
    wb.close()
    return rows


@router.post("/import")
async def import_users(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".csv")):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .csv 文件")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件不能超过 5MB")
    try:
        rows = _read_rows(file.filename, content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"文件解析失败：{exc}") from exc
    if not rows:
        raise HTTPException(status_code=400, detail="文件内容为空")

    header = rows[0]
    index = {}
    for i, cell in enumerate(header):
        key = cell.replace(" ", "")
        if key in ("姓名", "名字", "name"):
            index["name"] = i
        elif key in ("手机号", "手机", "电话", "phone"):
            index["phone"] = i
        elif key in ("部门", "department"):
            index["department"] = i
        elif key in ("角色", "role"):
            index["role"] = i
        elif key in ("账号", "用户名", "username", "account"):
            index["username"] = i
        elif key in ("初始密码", "密码", "password"):
            index["password"] = i
    if "phone" not in index or "name" not in index:
        raise HTTPException(status_code=400, detail="表头需包含“姓名”和“手机号”两列")

    created = updated = 0
    failed: list[dict] = []
    for row_no, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        phone = row[index["phone"]] if index["phone"] < len(row) else ""
        name = row[index["name"]] if index["name"] < len(row) else ""
        phone = re.sub(r"\.0$", "", phone.strip())
        if not phone or not name:
            failed.append({"row": row_no, "reason": "姓名或手机号为空"})
            continue
        if not re.match(r"^\d{5,20}$", phone):
            failed.append({"row": row_no, "reason": f"手机号格式不正确：{phone}"})
            continue
        department = row[index["department"]] if "department" in index and index["department"] < len(row) else ""
        role = role_from_text(row[index["role"]]) if "role" in index and index["role"] < len(row) else "employee"
        password = row[index["password"]] if "password" in index and index["password"] < len(row) else ""
        raw_username = (
            row[index["username"]] if "username" in index and index["username"] < len(row) else ""
        )
        existing = db.query(User).filter(User.phone == phone).first()
        try:
            username = None
            if role in STAFF_ROLES:
                username = clean_username(raw_username) if raw_username else (existing.username if existing else None)
                if not username:
                    failed.append({"row": row_no, "reason": "管理员/厨师需要填写「账号」列"})
                    continue
                assert_username_free(db, username, exclude_id=existing.id if existing else None)
            if existing:
                existing.name = name
                existing.department = department or existing.department
                existing.role = role
                existing.username = username
                existing.is_active = True
                if password:
                    existing.password_hash = hash_password(password)
                updated += 1
            else:
                db.add(
                    User(
                        phone=phone,
                        username=username,
                        name=name,
                        department=department,
                        role=role,
                        password_hash=hash_password(password or DEFAULT_PASSWORD),
                    )
                )
                created += 1
        except HTTPException as exc:
            failed.append({"row": row_no, "reason": exc.detail})
        except Exception as exc:  # noqa: BLE001
            failed.append({"row": row_no, "reason": str(exc)})
    db.commit()
    return {"created": created, "updated": updated, "failed": failed, "total": created + updated}


@router.get("/{user_id}/reservations")
def user_reservations(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Reservation)
        .filter(Reservation.user_id == user_id, Reservation.status == "reserved")
        .order_by(Reservation.date.desc())
        .limit(60)
        .all()
    )
    return [
        {"date": r.date.isoformat(), "meal": r.meal, "status": r.status} for r in rows
    ]
