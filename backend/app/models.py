from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    from .utils import local_now

    return local_now()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    # 管理端（管理员/厨师）登录账号；员工账号只用手机号登录，这里保持空。
    username: Mapped[str | None] = mapped_column(String(40), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="employee")
    department: Mapped[str] = mapped_column(String(60), default="")
    allergens: Mapped[str] = mapped_column(String(200), default="")  # 忌口
    preferences: Mapped[str] = mapped_column(String(300), default="")  # 饮食偏好
    taste: Mapped[str] = mapped_column(String(120), default="")  # 口味
    favorite_dishes: Mapped[str] = mapped_column(String(300), default="")  # 喜欢的菜
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="user")


class Menu(Base):
    __tablename__ = "menus"
    __table_args__ = (UniqueConstraint("date", "meal", name="uq_menu_date_meal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal: Mapped[str] = mapped_column(String(20), index=True)
    dishes: Mapped[str] = mapped_column(Text, default="[]")  # JSON: [{"name": "...", "type": "荤菜"}]
    note: Mapped[str] = mapped_column(String(300), default="")
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class DishTag(Base):
    """菜品类型标签（荤菜 / 素菜…）。

    仅作为「添加菜品时的选项缓存」，与菜单表无外键关联 ——
    菜单里保存的是当时输入的原始字符串，标签被删除不影响已有菜单。
    """

    __tablename__ = "dish_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (UniqueConstraint("user_id", "date", "meal", name="uq_reservation_user_date_meal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="reserved")  # reserved / cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    user: Mapped[User] = relationship(back_populates="reservations")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(30), default="other")
    content: Mapped[str] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal: Mapped[str] = mapped_column(String(20), default="")  # 关联餐次（可空）
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Review(Base):
    __tablename__ = "reviews"
    # 每人每天每个餐次一条评价（早/中/晚独立）
    __table_args__ = (UniqueConstraint("user_id", "date", "meal", name="uq_review_user_date_meal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal: Mapped[str] = mapped_column(String(20), default="lunch")  # breakfast / lunch / dinner
    rating: Mapped[int] = mapped_column(Integer)  # 5 非常好 / 4 很好 / 3 良好 / 2 一般 / 1 很差
    taste: Mapped[str] = mapped_column(String(30), default="")
    pairing: Mapped[str] = mapped_column(String(30), default="")
    portion: Mapped[str] = mapped_column(String(30), default="")
    comment: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Vote(Base):
    __tablename__ = "votes"
    # 每人每周可以投多道菜（多选），同一道菜不能重复投
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", "dish_name", name="uq_vote_user_week_dish"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    dish_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
