from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from .config import SECRET_KEY, TOKEN_EXPIRE_DAYS
from .utils import hash_password, verify_password

ALGORITHM = "HS256"


def create_token(user_id: int, role: str, scope: str = "app") -> str:
    # 时间戳必须用 UTC：PyJWT 会把 naive datetime 当作 UTC 处理，
    # 若直接塞本地时间（上海 +08:00）会让 iat 落在未来导致校验失败。
    # scope 区分员工端（app）与管理端（admin）两种凭证，互不通用。
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "scope": scope,
        "iat": now,
        "exp": now + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


__all__ = ["create_token", "decode_token", "hash_password", "verify_password"]
