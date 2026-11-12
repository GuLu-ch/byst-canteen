from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import date, datetime, time, timedelta

from .config import DEFAULT_SETTINGS, TZ


def local_now() -> datetime:
    """当前上海时间（naive，便于直接入库）。"""
    return datetime.now(TZ).replace(tzinfo=None, microsecond=0)


def today() -> date:
    return local_now().date()


def week_start_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_days(week_start: date) -> list[date]:
    return [week_start + timedelta(days=i) for i in range(7)]


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or base64.b16encode(os.urandom(8)).decode()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256$120000${salt}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, encoded = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(base64.b64encode(digest).decode(), encoded)
    except (ValueError, TypeError):
        return False


def json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_loads(value: str | None, default=None):
    if not value:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return default


def get_setting(db, key: str, default=None):
    from .models import Setting

    row = db.get(Setting, key)
    if row is None:
        return DEFAULT_SETTINGS.get(key, default)
    return json_loads(row.value, DEFAULT_SETTINGS.get(key, default))


def all_settings(db) -> dict:
    from .models import Setting

    values = dict(DEFAULT_SETTINGS)
    for row in db.query(Setting).all():
        values[row.key] = json_loads(row.value, values.get(row.key))
    return values


def save_setting(db, key: str, value) -> None:
    from .models import Setting

    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=json_dumps(value)))
    else:
        row.value = json_dumps(value)
    db.commit()


def deadline_for(settings: dict, meal: str, meal_date: date) -> datetime:
    """某天某餐的预约截止时间：前一天对应时刻。"""
    times = settings.get("deadline") or DEFAULT_SETTINGS["deadline"]
    hhmm = times.get(meal, "20:00")
    return datetime.combine(meal_date - timedelta(days=1), parse_hhmm(hhmm))


def reservation_state(settings: dict, meal: str, meal_date: date, now: datetime | None = None) -> dict:
    """返回某一餐是否可预约、截止时间、原因。"""
    now = now or local_now()
    deadline = deadline_for(settings, meal, meal_date)
    open_days = int(settings.get("open_days", 7) or 7)
    latest = today() + timedelta(days=open_days)
    reason = ""
    if meal_date.weekday() >= 5:
        reason = "周末不供餐"
    elif meal_date < today():
        reason = "该日期已过"
    elif meal_date > latest:
        reason = f"最多提前 {open_days} 天预约"
    elif now >= deadline:
        reason = "已过预约截止时间"
    return {
        "date": meal_date.isoformat(),
        "meal": meal,
        "deadline": deadline.isoformat(timespec="minutes"),
        "open": not reason,
        "reason": reason,
    }
