from __future__ import annotations

import argparse

from app.database import Base, SessionLocal, engine
from app.seed import seed


def main() -> None:
    parser = argparse.ArgumentParser(description="博涯小食堂数据库工具")
    parser.add_argument("--reset", action="store_true", help="删除并重建所有表（危险）")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(engine)
        print("已清空数据表")
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        created = seed(db)
        print("种子数据已生成" if created else "数据库已有数据，跳过种子数据")
    finally:
        db.close()


if __name__ == "__main__":
    main()
