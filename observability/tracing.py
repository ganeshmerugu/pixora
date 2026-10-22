from __future__ import annotations
import time
from typing import Any
from contextvars import ContextVar

_current_span: ContextVar[dict | None] = ContextVar("_current_span", default=None)


class Span:
    def __init__(self, name: str, attributes: dict[str, Any] | None = None):
        self.name = name
        self.attributes = attributes or {}
        self.start_time = time.monotonic()
        self.end_time: float | None = None
        self.events: list[dict[str, Any]] = []
        self.status = "ok"

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({"name": name, "time": time.monotonic(), "attributes": attributes or {}})

    def set_status(self, status: str) -> None:
        self.status = status

    def end(self) -> None:
        self.end_time = time.monotonic()

    @property
    def duration_ms(self) -> int:
        end = self.end_time or time.monotonic()
        return int((end - self.start_time) * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "attributes": self.attributes,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "events": self.events,
        }


class Tracer:
    def __init__(self, service_name: str = "pixora"):
        self.service_name = service_name
        self._spans: list[Span] = []

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Span:
        span = Span(name, attributes)
        self._spans.append(span)
        _current_span.set(span.to_dict())
        return span

    def get_traces(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._spans]

    def clear(self) -> None:
        self._spans.clear()


_default_tracer = Tracer()


def get_tracer() -> Tracer:
    return _default_tracer
