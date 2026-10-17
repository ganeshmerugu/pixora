from __future__ import annotations
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from pixora.auth.security import decode_token

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {
    "/api/v1/health",
    "/api/v1/budget",
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/google",
    "/api/v1/auth/google/callback",
    "/api/v1/auth/logout",
    "/api/docs",
    "/api/openapi.json",
    "/docs",
    "/openapi.json",
}

PUBLIC_PREFIXES = ("/assets/", "/static/")


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in PUBLIC_PATHS or path == "/" or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            request.state.user_id = None
            request.state.tenant_id = None
            request.state.user_email = None
            return await call_next(request)

        if not path.startswith("/api/"):
            request.state.user_id = None
            request.state.tenant_id = None
            request.state.user_email = None
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_token(token)
            if payload:
                request.state.user_id = payload.get("sub")
                request.state.tenant_id = payload.get("tenant_id")
                request.state.user_email = payload.get("email")
                return await call_next(request)

        api_key = request.headers.get("x-api-key", "")
        if api_key:
            request.state.user_id = "api_key_user"
            request.state.tenant_id = "api_key_tenant"
            request.state.user_email = None
            return await call_next(request)

        request.state.user_id = None
        request.state.tenant_id = None
        request.state.user_email = None
        return await call_next(request)
