"""DocMan-Anwendung."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.database import SessionLocal, ensure_dirs
from app.routes import HEADER, router
from app.seed import ensure_admin, ensure_samples
from app.services import rebuild_index

logger = logging.getLogger("docman")
STATIC = Path(__file__).resolve().parent.parent / "static"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def init_database() -> int:
    ensure_dirs()
    from app.database import Base, engine
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    from app.migrate import upgrade_schema

    upgrade_schema()
    with SessionLocal() as db:
        ensure_admin(db)
        ensure_samples(db)
        return rebuild_index(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.extend import start_watcher, stop_watcher

    count = init_database()
    start_watcher()
    logger.info("DocMan %s bereit, %s Dokumente im Index", __version__, count)
    try:
        yield
    finally:
        stop_watcher()


app = FastAPI(title="DocMan", version=__version__, lifespan=lifespan)
app.include_router(router)


@app.middleware("http")
async def protect(request: Request, call_next):
    if request.method in UNSAFE and request.url.path.startswith("/api/"):
        if request.headers.get(HEADER) != "1":
            return JSONResponse({"detail": "Fehlender Sicherheitsheader."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; script-src 'self'"
    )
    return response


@app.exception_handler(RequestValidationError)
async def invalid_body(_request: Request, _exc: RequestValidationError):
    return JSONResponse({"detail": "Ungültige Eingabe."}, status_code=422)


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Anfrage abgelehnt."
    return JSONResponse({"detail": detail}, status_code=exc.status_code)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=STATIC), name="static")
