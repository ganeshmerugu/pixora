from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pixora.api.routers import health, parse, extract, classify, quality, files
from pixora.api.routers import schemas, review, evals_router, webhooks, dashboard, audit, hitl, models
from pixora.api.routers import auth as auth_router, billing
from pixora.api.middleware.tenant import TenantMiddleware
from pixora.api.websocket import router as ws_router
import logging
import os
import time

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────
    from pixora.infra.monitoring import init_sentry, init_logging
    init_logging()
    init_sentry()
    logger.info("Pixora starting up...")

    # Init database
    try:
        from pixora.infra.database import init_db
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.warning("Database init skipped: %s", exc)

    # Seed admin account
    from pixora.auth.models import get_user_by_email, create_user
    from pixora.auth.security import hash_password
    if not get_user_by_email("admin@pixora.ai"):
        create_user(email="admin@pixora.ai", hashed_password=hash_password("admin123"), name="Admin")

    # Warm up Redis
    try:
        from pixora.infra.cache import get_redis
        r = await get_redis()
        if r:
            logger.info("Redis connected")
    except Exception:
        pass

    logger.info("Pixora ready")
    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("Pixora shutting down")


app = FastAPI(
    title="Pixora",
    version="1.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    description="AI-powered document intelligence platform.",
    lifespan=lifespan,
)

# ── Rate limiting middleware ──────────────────────────────────

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        from pixora.infra.cache import rate_limit_check
        from pixora.config.settings import settings

        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None) or client_ip
        limit = settings.rate_limit_parse_per_minute if "/parse" in request.url.path else settings.rate_limit_per_minute

        allowed, remaining = await rate_limit_check(f"{user_id}:{request.url.path}", limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute.", "retry_after": 60},
                headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
            )

    response = await call_next(request)
    return response

# ── Request logging middleware ────────────────────────────────

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = int((time.monotonic() - start) * 1000)

    if request.url.path.startswith("/api/") and not request.url.path.endswith("/health"):
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration,
                "user_id": getattr(request.state, "user_id", None),
            },
        )
    return response

app.add_middleware(TenantMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")

# Protected routes
app.include_router(files.router, prefix="/api/v1")
app.include_router(parse.router, prefix="/api/v1")
app.include_router(extract.router, prefix="/api/v1")
app.include_router(classify.router, prefix="/api/v1")
app.include_router(quality.router, prefix="/api/v1")
app.include_router(schemas.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(evals_router.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(hitl.router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")

# SPA frontend
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/pixora.svg")
    async def favicon():
        svg_path = os.path.join(_frontend_dist, "pixora.svg")
        if os.path.exists(svg_path):
            return FileResponse(svg_path, media_type="image/svg+xml")
        return FileResponse(os.path.join(_frontend_dist, "index.html"))

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
