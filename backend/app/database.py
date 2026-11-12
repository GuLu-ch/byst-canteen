from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DB_PATH

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """轻量迁移：SQLite 不支持 create_all 补列，这里按需 ALTER TABLE。

    只处理「老库缺新列/新表」这一种情况，重复执行也是安全的。
    """
    with engine.begin() as conn:
        tables = {row[0] for row in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")}
        # dish_tags 由 create_all 自动建表，这里只处理老 users 表补列
        if "users" not in tables:
            return
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)")}
        if "username" not in columns:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN username VARCHAR(40)")
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"
        )
