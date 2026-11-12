from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    phone: str = Field(min_length=4, max_length=20)
    password: str = Field(min_length=1, max_length=64)


class AdminLoginIn(BaseModel):
    """管理端登录：账号 + 密码（账号是管理员/厨师的登录名，不是手机号）。"""

    account: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=1, max_length=64)


class PasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=40)
    allergens: str | None = Field(default=None, max_length=200)
    preferences: str | None = Field(default=None, max_length=300)
    taste: str | None = Field(default=None, max_length=120)
    favorite_dishes: str | None = Field(default=None, max_length=300)


class UserIn(BaseModel):
    phone: str = Field(min_length=4, max_length=20)
    name: str = Field(min_length=1, max_length=40)
    role: str = "employee"
    department: str = ""
    password: str | None = None
    # 仅管理端账号（管理员/厨师）使用；员工账号用手机号登录。
    username: str | None = None


class UserUpdateIn(BaseModel):
    name: str | None = None
    role: str | None = None
    department: str | None = None
    is_active: bool | None = None
    password: str | None = None
    username: str | None = None


class ReservationItemIn(BaseModel):
    date: date
    meal: str


class BulkReservationIn(BaseModel):
    items: list[ReservationItemIn]


class MenuItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    type: str = Field(default="荤菜", max_length=20)


class MenuIn(BaseModel):
    dishes: list[MenuItemIn] = []
    note: str = Field(default="", max_length=300)


class FeedbackIn(BaseModel):
    category: str = "other"
    content: str = Field(min_length=1, max_length=1000)
    meal: str | None = None


class ReviewIn(BaseModel):
    date: date
    meal: str = "lunch"
    rating: int = Field(ge=1, le=5)
    taste: str = ""
    pairing: str = ""
    portion: str = ""
    comment: str = Field(default="", max_length=500)


class VoteIn(BaseModel):
    week_start: date
    # 支持多选：dish_names 为空列表表示清空本周投票
    dish_names: list[str] = Field(default_factory=list)
    dish_name: str | None = None

    def resolved_names(self) -> list[str]:
        names = list(self.dish_names)
        if self.dish_name:
            names.append(self.dish_name)
        seen: list[str] = []
        for name in names:
            name = (name or "").strip()
            if name and name not in seen:
                seen.append(name)
        return seen


class SettingsIn(BaseModel):
    values: dict[str, Any]
