from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import ADMIN_COOKIE
from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def _resolve_token(
    request: Request | None,
    credentials: HTTPAuthorizationCredentials | None,
    scope: str,
) -> str | None:
    """取当前请求的凭证。

    管理端：优先 httpOnly cookie（浏览器自动携带），其次 Authorization 头（接口调试用）。
    用户端：只用 Authorization 头（token 存在 localStorage）。
    """
    if scope == "admin" and request is not None:
        cookie = request.cookies.get(ADMIN_COOKIE)
        if cookie:
            return cookie
    if credentials is not None:
        return credentials.credentials
    return None


def _load_user(token: str | None, db: Session, scope: str) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
    # scope 校验：员工端（app）与管理端（admin）凭证互不通用。
    if payload.get("scope", "app") != scope:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请使用正确的入口登录")
    user = db.get(User, int(payload.get("sub", 0)))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已停用")
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """员工端身份（scope=app）。"""
    return _load_user(_resolve_token(request, credentials, "app"), db, "app")


def get_admin_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """管理端身份（scope=admin），浏览器场景下凭证来自 httpOnly cookie。"""
    return _load_user(_resolve_token(request, credentials, "admin"), db, "admin")


def get_any_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """两端共用的只读接口：接受员工 token 或管理端 cookie/token。"""
    token = _resolve_token(request, credentials, "admin")
    if token:
        payload = decode_token(token)
        if payload and payload.get("scope", "app") in ("app", "admin"):
            user = db.get(User, int(payload.get("sub", 0)))
            if user is not None and user.is_active:
                return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")


def scope_user(scope: str):
    """指定 scope 的身份依赖。"""

    def dep(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        db: Session = Depends(get_db),
    ) -> User:
        return _load_user(_resolve_token(request, credentials, scope), db, scope)

    return dep


def require_roles(*roles: str, scope: str = "admin"):
    """管理端接口默认使用 scope=admin 的凭证。"""

    def checker(user: User = Depends(scope_user(scope))) -> User:
        if roles and user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限执行该操作")
        return user

    return checker


require_staff = require_roles("admin", "cook")
require_admin = require_roles("admin")
