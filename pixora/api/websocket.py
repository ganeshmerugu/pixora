from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_job_subscribers: dict[str, list[WebSocket]] = {}


async def broadcast_job_event(job_id: str, event: dict) -> None:
    sockets = _job_subscribers.get(job_id, [])
    dead: list[WebSocket] = []
    for ws in sockets:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        sockets.remove(ws)


@router.websocket("/jobs/{job_id}/stream")
async def job_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    _job_subscribers.setdefault(job_id, []).append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        subs = _job_subscribers.get(job_id, [])
        if websocket in subs:
            subs.remove(websocket)
