from __future__ import annotations
from typing import Any, Callable, Awaitable


class CallbackRegistry:
    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[..., Awaitable[None]]]] = {}

    def register(self, event: str, callback: Callable[..., Awaitable[None]]) -> None:
        self._hooks.setdefault(event, []).append(callback)

    async def fire(self, event: str, **kwargs: Any) -> None:
        for cb in self._hooks.get(event, []):
            await cb(**kwargs)

    def list_events(self) -> list[str]:
        return list(self._hooks.keys())
