from __future__ import annotations
import re
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator
from pixora.auth.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
)
from pixora.auth.models import (
    create_user, get_user_by_email, get_user_by_google_id,
    get_tenant_for_user, store_refresh_token, validate_refresh_token,
    revoke_refresh_token, User,
)
from pixora.auth.dependencies import get_current_user
from pixora.auth.oauth import (
    get_google_auth_url, exchange_google_code, is_google_oauth_configured,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str = ""

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: dict


@router.post("/signup", response_model=TokenResponse)
async def signup(req: SignupRequest):
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password(req.password)
    try:
        user = create_user(email=req.email, hashed_password=hashed, name=req.name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    tenant = get_tenant_for_user(user["id"])

    access_token = create_access_token({"sub": user["id"], "email": user["email"], "tenant_id": tenant["id"] if tenant else ""})
    refresh_token = create_refresh_token({"sub": user["id"]})
    store_refresh_token(user["id"], refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_sanitize_user(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = get_user_by_email(req.email.lower().strip())
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="This account uses Google sign-in. Please login with Google.")

    if not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tenant = get_tenant_for_user(user["id"])

    access_token = create_access_token({"sub": user["id"], "email": user["email"], "tenant_id": tenant["id"] if tenant else ""})
    refresh_token = create_refresh_token({"sub": user["id"]})
    store_refresh_token(user["id"], refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_sanitize_user(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest):
    user_id = validate_refresh_token(req.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    from pixora.auth.models import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    revoke_refresh_token(req.refresh_token)

    tenant = get_tenant_for_user(user["id"])
    access_token = create_access_token({"sub": user["id"], "email": user["email"], "tenant_id": tenant["id"] if tenant else ""})
    new_refresh = create_refresh_token({"sub": user["id"]})
    store_refresh_token(user["id"], new_refresh)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=_sanitize_user(user),
    )


@router.get("/google")
async def google_login():
    if not is_google_oauth_configured():
        raise HTTPException(status_code=503, detail="Google OAuth not configured. Set PIXORA_GOOGLE_CLIENT_ID and PIXORA_GOOGLE_CLIENT_SECRET.")
    url = get_google_auth_url()
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str = "", error: str = ""):
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        google_info = await exchange_google_code(code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to exchange Google code: {exc}")

    google_id = google_info["google_id"]
    email = google_info["email"]

    user = get_user_by_google_id(google_id)
    if not user:
        user = get_user_by_email(email)
        if user:
            user["google_id"] = google_id
            user["avatar_url"] = google_info.get("avatar_url", "")
        else:
            user = create_user(
                email=email,
                name=google_info.get("name", ""),
                google_id=google_id,
            )
            user["avatar_url"] = google_info.get("avatar_url", "")

    tenant = get_tenant_for_user(user["id"])
    access_token = create_access_token({"sub": user["id"], "email": user["email"], "tenant_id": tenant["id"] if tenant else ""})
    refresh_token = create_refresh_token({"sub": user["id"]})
    store_refresh_token(user["id"], refresh_token)

    return RedirectResponse(
        url=f"/?token={access_token}&refresh={refresh_token}"
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    tenant = get_tenant_for_user(user["id"])
    from pixora.auth.models import check_quota
    quota = check_quota(tenant["id"]) if tenant else {}

    return {
        "user": _sanitize_user(user),
        "tenant": dict(tenant) if tenant else None,
        "quota": quota,
    }


@router.post("/logout")
async def logout(req: RefreshRequest):
    revoke_refresh_token(req.refresh_token)
    return {"message": "Logged out successfully"}


def _sanitize_user(user: User) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "avatar_url": user.get("avatar_url", ""),
        "is_verified": user.get("is_verified", False),
        "created_at": user.get("created_at", ""),
    }
