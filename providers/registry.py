from __future__ import annotations
from typing import Any


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}

    def register(self, capability: str, provider: Any, priority: int = 0) -> None:
        self._providers[capability] = provider

    def get(self, capability: str) -> Any:
        if capability not in self._providers:
            raise KeyError(f"No provider registered for capability: {capability}")
        return self._providers[capability]

    def swap(self, capability: str, new_provider: Any) -> None:
        self._providers[capability] = new_provider

    def list_providers(self) -> dict[str, str]:
        return {cap: p.provider_name for cap, p in self._providers.items()}
