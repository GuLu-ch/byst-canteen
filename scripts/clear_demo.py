"""上线前清空演示数据。

保留：管理员 / 厨师账号（users 里 role != employee）、系统设置（settings）、菜品标签（dish_tags）。
清空：菜单、预约、评价、反馈、投票，以及演示员工（role == employee）。

用法（在 backend 目录下，虚拟环境里执行）：

    python ../scripts/clear_demo.py --yes

不加 --yes 只打印将要清空的数量，不动数据库。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 允许从任意目录执行：把 backend/ 加进模块搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402


def collect(db):
    return {
        "menus": db.query(models.Menu).count(),
        "reservations": db.query(models.Reservation).count(),
        "reviews": db.query(models.Review).count(),
        "feedback": db.query(models.Feedback).count(),
        "votes": db.query(models.Vote).count(),
        "employees": db.query(models.User).filter(models.User.role == "employee").count(),
    }


def main() -> int:
    confirmed = "--yes" in sys.argv or "-y" in sys.argv

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        counts = collect(db)
        print("将要清空：")
        for key, value in counts.items():
            print(f"  {key:<14}{value}")

        if not confirmed:
            print("\n这是预演，未修改数据库。确认执行请加 --yes")
            return 0

        db.query(models.Vote).delete()
        db.query(models.Review).delete()
        db.query(models.Reservation).delete()
        db.query(models.Feedback).delete()
        db.query(models.Menu).delete()
        db.query(models.User).filter(models.User.role == "employee").delete()
        db.commit()
        print("\n已清空演示数据；管理员/厨师账号、系统设置、菜品标签保留。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
