from __future__ import annotations
import hashlib
import hmac
import os
import secrets
import time
from typing import Any

try:
    from jose import jwt, JWTError
    HAS_JOSE = True
except ImportError:
    jwt = None  # type: ignore[assignment]
    JWTError = Exception  # type: ignore[misc,assignment]
    HAS_JOSE = False

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    bcrypt = None  # type: ignore[assignment]
    HAS_BCRYPT = False

SECRET_KEY = os.environ.get("PIXORA_JWT_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 1800
REFRESH_TOKEN_EXPIRE_SECONDS = 604800


def hash_password(password: str) -> str:
    if HAS_BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    if HAS_BCRYPT:
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except Exception:
            return False
    return hashlib.sha256(password.encode()).hexdigest() == hashed


def create_access_token(data: dict[str, Any], expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
    if not HAS_JOSE:
        return _fallback_token(data, expires_in)
    payload = {**data, "exp": int(time.time()) + expires_in, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict[str, Any], expires_in: int = REFRESH_TOKEN_EXPIRE_SECONDS) -> str:
    if not HAS_JOSE:
        return _fallback_token(data, expires_in)
    payload = {**data, "exp": int(time.time()) + expires_in, "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    if not HAS_JOSE:
        return _fallback_decode(token)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    raw_key = f"px_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    return hashlib.sha256(raw_key.encode()).hexdigest() == key_hash


def _fallback_token(data: dict, expires_in: int) -> str:
    import json, base64
    payload = {**data, "exp": int(time.time()) + expires_in}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload_b64}.{sig}"


def _fallback_decode(token: str) -> dict[str, Any] | None:
    import json, base64
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
