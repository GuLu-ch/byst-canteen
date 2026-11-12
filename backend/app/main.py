from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  确保模型注册
from .config import FRONTEND_DIST
from .database import Base, SessionLocal, engine, ensure_schema
from .routers import auth, feedback, menus, reservations, reviews, settings, stats, users, votes
from .seed import ensure_staff_accounts, seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    ensure_schema()
    db = SessionLocal()
    try:
        seed(db)
        ensure_staff_accounts(db)
    finally:
        db.close()
    yield


app = FastAPI(title="博涯小食堂 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    users.router,
    menus.router,
    reservations.router,
    feedback.router,
    reviews.router,
    votes.router,
    stats.router,
    settings.router,
):
    app.include_router(router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "博涯小食堂"}


if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="接口不存在")
    if not (FRONTEND_DIST / "index.html").exists():
        return JSONResponse(
            {
                "message": "前端尚未构建。开发模式请访问 http://localhost:5173，或先执行 npm run build。",
                "api": "/docs",
            },
            status_code=200,
        )
    target = (FRONTEND_DIST / full_path).resolve()
    if full_path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
        return FileResponse(target)
    return FileResponse(FRONTEND_DIST / "index.html")
