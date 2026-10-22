from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pixora.api.routers import health, parse, extract, classify, quality, files
from pixora.api.routers import schemas, review, evals_router, webhooks, dashboard, audit, hitl, models
from pixora.api.routers import auth as auth_router, billing
from pixora.api.middleware.tenant import TenantMiddleware
from pixora.api.websocket import router as ws_router
import os

app = FastAPI(
    title="Pixora",
    version="0.2.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    description="AI-powered document intelligence platform. Extract, classify, and understand any document.",
)


@app.on_event("startup")
def _seed_admin():
    from pixora.auth.models import get_user_by_email, create_user
    from pixora.auth.security import hash_password
    if not get_user_by_email("admin@pixora.ai"):
        create_user(
            email="admin@pixora.ai",
            hashed_password=hash_password("admin123"),
            name="Admin",
        )

_allowed_origins = os.environ.get("PIXORA_ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(TenantMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.environ.get("PIXORA_ENV") == "production":
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    _allowed_hosts = os.environ.get("PIXORA_ALLOWED_HOSTS", "*").split(",")
    if _allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

# Public routes (no auth required)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")

# Protected routes (auth optional for now, enforced per-endpoint)
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

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
_index_html = os.path.join(frontend_dir, "index.html")

if os.path.isdir(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="static-assets")

    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str):
        file_path = os.path.join(frontend_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(_index_html)
