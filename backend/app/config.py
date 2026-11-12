from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("BYST_DB", BASE_DIR / "data" / "byst.db"))
FRONTEND_DIST = Path(os.getenv("BYST_DIST", BASE_DIR.parent / "frontend" / "dist"))

SECRET_KEY = os.getenv("BYST_SECRET", "byst-canteen-dev-secret-change-me")
TOKEN_EXPIRE_DAYS = int(os.getenv("BYST_TOKEN_DAYS", "7"))
TZ = ZoneInfo("Asia/Shanghai")

# 管理端凭证走独立的 httpOnly cookie，与用户端（localStorage token）完全隔离。
ADMIN_COOKIE = "byst_admin"
ADMIN_COOKIE_MAX_AGE = TOKEN_EXPIRE_DAYS * 24 * 3600

MEALS = ("breakfast", "lunch", "dinner")
MEAL_LABELS = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}
ROLES = ("employee", "cook", "admin")
ROLE_LABELS = {"employee": "员工", "cook": "厨师", "admin": "管理员"}

DEFAULT_SETTINGS = {
    "canteen_name": "博涯小食堂",
    "announcement": "本周五午餐加餐：红烧排骨、蒜蓉西兰花，欢迎品尝～",
    "meal_times": {
        "breakfast": "07:30 - 08:30",
        "lunch": "11:30 - 12:30",
        "dinner": "17:30 - 18:30",
    },
    "deadline": {
        "breakfast": "20:00",
        "lunch": "20:00",
        "dinner": "20:00",
    },
    "open_days": 7,
    "feedback_enabled": True,
    "review_enabled": True,
    "vote_enabled": True,
}
