from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import DEFAULT_SETTINGS, MEALS
from ..database import get_db
from ..deps import require_admin
from ..models import Setting, User
from ..schemas import SettingsIn
from ..utils import all_settings, json_dumps, local_now

router = APIRouter(prefix="/api/settings", tags=["settings"])

HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

PUBLIC_KEYS = (
    "canteen_name",
    "announcement",
    "meal_times",
    "deadline",
    "open_days",
    "feedback_enabled",
    "review_enabled",
    "vote_enabled",
)


@router.get("/public")
def public_settings(db: Session = Depends(get_db)):
    """登录前也要能拿到（登录页展示食堂名称、公告、就餐时间）。"""
    values = all_settings(db)
    return {
        **{key: values.get(key, DEFAULT_SETTINGS.get(key)) for key in PUBLIC_KEYS},
        "server_time": local_now().isoformat(timespec="minutes"),
    }


@router.get("")
def get_settings(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return all_settings(db)


@router.put("")
def update_settings(
    payload: SettingsIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    values = payload.values
    if "deadline" in values:
        deadline = values["deadline"]
        if not isinstance(deadline, dict):
            raise HTTPException(status_code=400, detail="截止时间格式不正确")
        for meal in MEALS:
            if meal in deadline and not HHMM_RE.match(str(deadline[meal])):
                raise HTTPException(status_code=400, detail="截止时间需为 HH:MM 格式")
    if "open_days" in values:
        try:
            days = int(values["open_days"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="可预约天数需为数字") from exc
        if not 1 <= days <= 30:
            raise HTTPException(status_code=400, detail="可预约天数需在 1-30 之间")
        values["open_days"] = days
    if "meal_times" in values and not isinstance(values["meal_times"], dict):
        raise HTTPException(status_code=400, detail="就餐时间格式不正确")
    if "canteen_name" in values and not str(values["canteen_name"]).strip():
        raise HTTPException(status_code=400, detail="食堂名称不能为空")

    for key, value in values.items():
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=json_dumps(value)))
        else:
            row.value = json_dumps(value)
    db.commit()
    return all_settings(db)
