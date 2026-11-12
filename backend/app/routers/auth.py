from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..config import ADMIN_COOKIE, ADMIN_COOKIE_MAX_AGE
from ..database import get_db
from ..deps import get_admin_user, get_current_user
from ..models import User
from ..schemas import AdminLoginIn, LoginIn, PasswordIn, ProfileIn
from ..security import create_token, verify_password
from ..serializers import user_out
from ..utils import hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

PHONE_RE = re.compile(r"^\d{5,20}$")
STAFF_ROLES = ("admin", "cook")


def _check_active(user: User) -> None:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用，请联系管理员")


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """用户端（员工）登录：手机号 + 密码，管理端账号不能从这里进入。"""
    phone = payload.phone.strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=400, detail="请输入正确的手机号")
    user = db.query(User).filter(User.phone == phone).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="手机号或密码错误")
    _check_active(user)
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="该账号是管理端账号，请从管理后台登录")
    return {"token": create_token(user.id, user.role, "app"), "user": user_out(user)}


@router.post("/admin-login")
def admin_login(payload: AdminLoginIn, response: Response, db: Session = Depends(get_db)):
    """管理端登录：账号 + 密码（账号为管理员/厨师账号，不是手机号）。

    成功后把管理端 token 写进独立的 httpOnly cookie，前端 JS 读不到，
    与员工端的 localStorage token 互不影响。
    """
    account = payload.account.strip()
    if not account:
        raise HTTPException(status_code=400, detail="请输入账号")
    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == account.lower(),
                User.phone == account,
            )
        )
        .first()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="账号或密码错误")
    _check_active(user)
    if user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="该账号不是管理端账号")
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=create_token(user.id, user.role, "admin"),
        max_age=ADMIN_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"user": user_out(user)}


@router.post("/admin-logout")
def admin_logout(response: Response):
    """退出管理端：清掉管理端 cookie。"""
    response.delete_cookie(ADMIN_COOKIE, path="/")
    return {"message": "已退出登录"}


@router.post("/password")
def change_password(
    payload: PasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "密码修改成功"}


@router.post("/admin-password")
def change_admin_password(
    payload: PasswordIn,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理端账号修改自己的密码。"""
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "密码修改成功"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.get("/admin-me")
def admin_me(user: User = Depends(get_admin_user)):
    """管理端会话信息（cookie 或 admin scope token）。"""
    return user_out(user)


@router.put("/profile")
def update_profile(
    payload: ProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    if not (data.get("name") or "").strip() and "name" in data:
        raise HTTPException(status_code=400, detail="姓名不能为空")
    for key, value in data.items():
        if value is not None:
            setattr(user, key, value.strip())
    db.commit()
    db.refresh(user)
    return user_out(user)
