from __future__ import annotations
from typing import Any
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pixora.auth.security import decode_token
from pixora.auth.models import (
    get_user_by_id, get_tenant_for_user, get_user_role,
    check_quota, increment_docs_used, User, Tenant,
)

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_id(user_id)
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        if not payload:
            return None
        user = get_user_by_id(payload.get("sub", ""))
        return user
    except Exception:
        return None


async def get_current_tenant(
    user: User = Depends(get_current_user),
) -> Tenant:
    tenant = get_tenant_for_user(user["id"])
    if not tenant:
        raise HTTPException(status_code=403, detail="No tenant associated with user")
    return tenant


def require_role(*roles: str):
    async def _check(
        user: User = Depends(get_current_user),
        tenant: Tenant = Depends(get_current_tenant),
    ):
        role = get_user_role(user["id"], tenant["id"])
        if role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' not authorized. Required: {', '.join(roles)}",
            )
        return user
    return _check


async def enforce_quota(
    tenant: Tenant = Depends(get_current_tenant),
) -> Tenant:
    quota = check_quota(tenant["id"])
    if not quota["allowed"]:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "plan": quota["plan"],
                "docs_used": quota["docs_used"],
                "docs_limit": quota["docs_limit"],
                "message": f"You've used all {quota['docs_limit']} documents on your {quota['plan']} plan. Upgrade to continue.",
                "upgrade_url": "/billing/upgrade",
            },
        )
    return tenant
