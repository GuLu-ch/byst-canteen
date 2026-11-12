from __future__ import annotations

from .models import Feedback, Menu, Reservation, Review, User, Vote
from .utils import json_loads


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "username": user.username or "",
        # 管理端展示用：管理员/厨师显示登录账号，员工显示手机号
        "account": (user.username or user.phone) if user.role != "employee" else user.phone,
        "name": user.name,
        "role": user.role,
        "department": user.department,
        "allergens": user.allergens,
        "preferences": user.preferences,
        "taste": user.taste,
        "favorite_dishes": user.favorite_dishes,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(timespec="minutes") if user.created_at else None,
    }


def menu_out(menu: Menu | None, date_value=None, meal: str | None = None) -> dict:
    if menu is None:
        return {
            "date": (date_value.isoformat() if date_value else None),
            "meal": meal,
            "dishes": [],
            "note": "",
            "updated_at": None,
        }
    return {
        "date": menu.date.isoformat(),
        "meal": menu.meal,
        "dishes": json_loads(menu.dishes, []),
        "note": menu.note,
        "updated_at": menu.updated_at.isoformat(timespec="minutes") if menu.updated_at else None,
    }


def reservation_out(item: Reservation) -> dict:
    return {
        "id": item.id,
        "date": item.date.isoformat(),
        "meal": item.meal,
        "status": item.status,
        "created_at": item.created_at.isoformat(timespec="minutes") if item.created_at else None,
    }


def feedback_out(item: Feedback) -> dict:
    # 匿名：绝不返回 user_id / 姓名 / 手机号
    return {
        "id": item.id,
        "category": item.category,
        "content": item.content,
        "date": item.date.isoformat(),
        "meal": item.meal or None,
        "handled": item.handled,
        "created_at": item.created_at.isoformat(timespec="minutes") if item.created_at else None,
    }


def review_out(item: Review) -> dict:
    return {
        "id": item.id,
        "date": item.date.isoformat(),
        "meal": item.meal,
        "rating": item.rating,
        "taste": item.taste,
        "pairing": item.pairing,
        "portion": item.portion,
        "comment": item.comment,
        "created_at": item.created_at.isoformat(timespec="minutes") if item.created_at else None,
    }


def vote_out(item: Vote) -> dict:
    return {
        "id": item.id,
        "week_start": item.week_start.isoformat(),
        "dish_name": item.dish_name,
        "created_at": item.created_at.isoformat(timespec="minutes") if item.created_at else None,
    }
