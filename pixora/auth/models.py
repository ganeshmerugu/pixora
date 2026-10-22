from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any
from typing_extensions import Required, TypedDict


CURRENCY_RATES: dict[str, dict] = {
    "USD": {"symbol": "$", "rate": 1.0},
    "INR": {"symbol": "₹", "rate": 84.0},
    "EUR": {"symbol": "€", "rate": 0.92},
    "GBP": {"symbol": "£", "rate": 0.79},
    "BRL": {"symbol": "R$", "rate": 5.0},
    "JPY": {"symbol": "¥", "rate": 149.0},
    "AED": {"symbol": "AED", "rate": 3.67},
    "SGD": {"symbol": "S$", "rate": 1.34},
    "AUD": {"symbol": "A$", "rate": 1.53},
    "CAD": {"symbol": "C$", "rate": 1.36},
}

PLAN_LIMITS = {
    "free_trial": {"docs_limit": 50, "monthly": False, "price_usd": 0},
    "starter": {"docs_limit": 200, "monthly": True, "price_usd": 9},
    "pro": {"docs_limit": 1000, "monthly": True, "price_usd": 29},
    "enterprise": {"docs_limit": 999999, "monthly": True, "price_usd": 0},
}


def get_localized_price(price_usd: float, currency: str = "USD") -> dict:
    info = CURRENCY_RATES.get(currency, CURRENCY_RATES["USD"])
    local_price = round(price_usd * info["rate"])
    if currency in ("JPY", "INR"):
        local_price = round(price_usd * info["rate"], 0)
    else:
        local_price = round(price_usd * info["rate"], 2)
    return {
        "amount": local_price,
        "currency": currency,
        "symbol": info["symbol"],
        "display": f"{info['symbol']}{local_price:,.0f}" if local_price == int(local_price) else f"{info['symbol']}{local_price:,.2f}",
    }


class User(TypedDict, total=False):
    id: Required[str]
    email: Required[str]
    hashed_password: str
    name: str
    google_id: str
    avatar_url: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: str
    metadata: dict[str, Any]


class Tenant(TypedDict, total=False):
    id: Required[str]
    name: Required[str]
    plan: Required[str]
    docs_used: int
    docs_limit: int
    billing_email: str
    stripe_customer_id: str
    created_at: str
    plan_started_at: str
    metadata: dict[str, Any]


class TenantMember(TypedDict, total=False):
    user_id: Required[str]
    tenant_id: Required[str]
    role: Required[str]
    joined_at: str


class APIKey(TypedDict, total=False):
    id: Required[str]
    tenant_id: Required[str]
    key_hash: Required[str]
    name: str
    prefix: str
    created_at: str
    last_used: str
    is_active: bool


# --- In-memory stores (swap to DB for production) ---

_users: dict[str, User] = {}
_tenants: dict[str, Tenant] = {}
_members: list[TenantMember] = []
_api_keys: dict[str, APIKey] = {}
_refresh_tokens: dict[str, str] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_user(
    email: str,
    hashed_password: str = "",
    name: str = "",
    google_id: str = "",
) -> User:
    for u in _users.values():
        if u["email"] == email:
            raise ValueError(f"User with email '{email}' already exists")

    user_id = uuid.uuid4().hex[:16]
    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        name=name or email.split("@")[0],
        google_id=google_id,
        is_active=True,
        is_verified=bool(google_id),
        created_at=_now(),
    )
    _users[user_id] = user

    tenant = create_tenant(name=f"{user['name']}'s Workspace", owner_id=user_id)

    return user


def create_tenant(name: str, owner_id: str, plan: str = "free_trial") -> Tenant:
    tenant_id = uuid.uuid4().hex[:16]
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free_trial"])
    tenant = Tenant(
        id=tenant_id,
        name=name,
        plan=plan,
        docs_used=0,
        docs_limit=limits["docs_limit"],
        created_at=_now(),
        plan_started_at=_now(),
    )
    _tenants[tenant_id] = tenant

    _members.append(TenantMember(
        user_id=owner_id,
        tenant_id=tenant_id,
        role="admin",
        joined_at=_now(),
    ))

    return tenant


def get_user_by_email(email: str) -> User | None:
    for u in _users.values():
        if u["email"] == email:
            return u
    return None


def get_user_by_id(user_id: str) -> User | None:
    return _users.get(user_id)


def get_user_by_google_id(google_id: str) -> User | None:
    for u in _users.values():
        if u.get("google_id") == google_id:
            return u
    return None


def get_tenant_for_user(user_id: str) -> Tenant | None:
    for m in _members:
        if m["user_id"] == user_id:
            return _tenants.get(m["tenant_id"])
    return None


def get_user_role(user_id: str, tenant_id: str) -> str | None:
    for m in _members:
        if m["user_id"] == user_id and m["tenant_id"] == tenant_id:
            return m["role"]
    return None


def increment_docs_used(tenant_id: str, count: int = 1) -> bool:
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return False
    current = tenant.get("docs_used", 0)
    limit = tenant.get("docs_limit", 50)
    if current + count > limit:
        return False
    tenant["docs_used"] = current + count
    return True


def check_quota(tenant_id: str) -> dict[str, Any]:
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return {"allowed": False, "reason": "tenant_not_found"}
    used = tenant.get("docs_used", 0)
    limit = tenant.get("docs_limit", 50)
    return {
        "allowed": used < limit,
        "docs_used": used,
        "docs_limit": limit,
        "remaining": max(0, limit - used),
        "plan": tenant.get("plan", "free_trial"),
        "reason": "quota_exceeded" if used >= limit else "ok",
    }


def upgrade_plan(tenant_id: str, new_plan: str) -> Tenant | None:
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return None
    limits = PLAN_LIMITS.get(new_plan)
    if not limits:
        return None
    tenant["plan"] = new_plan
    tenant["docs_limit"] = limits["docs_limit"]
    tenant["plan_started_at"] = _now()
    if limits["monthly"]:
        tenant["docs_used"] = 0
    return tenant


def store_refresh_token(user_id: str, token: str) -> None:
    _refresh_tokens[token] = user_id


def validate_refresh_token(token: str) -> str | None:
    return _refresh_tokens.get(token)


def revoke_refresh_token(token: str) -> None:
    _refresh_tokens.pop(token, None)
