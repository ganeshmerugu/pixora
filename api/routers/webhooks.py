from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_webhooks: dict[str, dict] = {}


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=lambda: ["job.completed"])
    secret: str = ""


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool = True


@router.post("", response_model=WebhookResponse)
async def create_webhook(request: WebhookCreateRequest):
    wh_id = uuid.uuid4().hex[:16]
    data = {"id": wh_id, "url": request.url, "events": request.events, "active": True}
    _webhooks[wh_id] = data
    return WebhookResponse(**data)


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks():
    return [WebhookResponse(**w) for w in _webhooks.values()]


@router.get("/{wh_id}", response_model=WebhookResponse)
async def get_webhook(wh_id: str):
    w = _webhooks.get(wh_id)
    if not w:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return WebhookResponse(**w)


@router.put("/{wh_id}", response_model=WebhookResponse)
async def update_webhook(wh_id: str, request: WebhookCreateRequest):
    if wh_id not in _webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    _webhooks[wh_id].update(url=request.url, events=request.events)
    return WebhookResponse(**_webhooks[wh_id])


@router.delete("/{wh_id}")
async def delete_webhook(wh_id: str):
    if wh_id not in _webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    del _webhooks[wh_id]
    return {"deleted": True}


def dispatch_all(event: str, payload: dict):
    import threading
    import httpx
    import hashlib
    import json

    for wh in _webhooks.values():
        if not wh.get("active"):
            continue
        if event not in wh.get("events", []):
            continue
        url = wh["url"]
        secret = wh.get("secret", "")

        def _send(u=url, s=secret):
            try:
                body = json.dumps({"event": event, **payload}, default=str)
                sig = hashlib.hmac_new(s.encode(), body.encode(), hashlib.sha256).hexdigest() if s else ""
                headers = {"Content-Type": "application/json"}
                if sig:
                    headers["X-Pixora-Signature"] = sig
                httpx.post(u, content=body, headers=headers, timeout=10.0)
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()
