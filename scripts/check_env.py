"""部署自检：一条命令看清「依赖装没装对、前端产物在不在、数据库能不能写」。

用法（在服务器上，用**项目实际运行的 Python** 执行）：

    /www/wwwroot/byts/venv/bin/python scripts/check_env.py

也可以直接在宝塔「Python项目」的启动命令前面挂它，先看输出再启动。
"""
from __future__ import annotations

import importlib.metadata as md
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# 运行时真正需要的包（和 backend/requirements.txt 对齐）
REQUIRED = [
    "fastapi",
    "uvicorn",
    "python-multipart",
    "SQLAlchemy",
    "PyJWT",
    "openpyxl",
    "pydantic",
]


def check_packages() -> bool:
    print(f"Python: {sys.version.split()[0]}  ({sys.executable})")
    ok = True
    for name in REQUIRED:
        try:
            version = md.version(name)
        except Exception:
            print(f"  ✗ {name:<18}未安装")
            ok = False
            continue
        print(f"  ✓ {name:<18}{version}")
    return ok


def check_frontend() -> bool:
    dist = Path(os.getenv("BYST_DIST", ROOT / "frontend" / "dist"))
    index = dist / "index.html"
    assets = dist / "assets"
    if not index.exists():
        print(f"  ✗ 前端未构建：{index} 不存在（页面会显示一段 JSON 提示）")
        return False
    count = len(list(assets.glob("*"))) if assets.exists() else 0
    print(f"  ✓ 前端产物：{dist}（assets 里 {count} 个文件）")
    return True


def check_database() -> bool:
    db_path = Path(os.getenv("BYST_DB", BACKEND / "data" / "byst.db"))
    parent = db_path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        print(f"  ✗ 无法创建数据目录 {parent}：{error}")
        return False
    if not os.access(parent, os.W_OK):
        print(f"  ✗ 数据目录不可写（{parent}）—— 多半是属主不是 www，执行：chown -R www:www {parent}")
        return False
    if db_path.exists():
        size = db_path.stat().st_size / 1024
        print(f"  ✓ 数据库：{db_path}（{size:.0f} KB）")
    else:
        print(f"  ✓ 数据库：{db_path}（尚未创建，首次启动会自动建表并写入演示数据）")
    return True


def main() -> int:
    print("== 依赖 ==")
    deps_ok = check_packages()

    print("\n== 前端 ==")
    fe_ok = check_frontend()

    print("\n== 数据库 ==")
    db_ok = check_database()

    print("\n== 结论 ==")
    if deps_ok and db_ok:
        print("后端具备启动条件。启动后可执行：curl http://127.0.0.1:8000/api/health")
        if not fe_ok:
            print("提醒：前端还没构建/没上传，接口能用但页面打不开。")
        return 0
    if not deps_ok:
        print("依赖缺失：请用**本项目的虚拟环境**安装 -> pip install -r backend/requirements.txt")
        print("如果装完还缺，说明你装到了别的 Python 里：确认 sys.executable（上面那行）就是启动命令用的那个。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
