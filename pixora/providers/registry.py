from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Any] = {}
        self._fallback_chains: dict[str, list[Any]] = {}

    def register(self, capability: str, provider: Any, priority: int = 0) -> None:
        self._providers[capability] = provider
        if capability not in self._fallback_chains:
            self._fallback_chains[capability] = []
        chain = self._fallback_chains[capability]
        chain.append((priority, provider))
        chain.sort(key=lambda x: x[0])

    def get(self, capability: str) -> Any:
        if capability not in self._providers:
            raise KeyError(f"No provider registered for capability: {capability}")
        return self._providers[capability]

    def get_fallback_chain(self, capability: str) -> list[Any]:
        chain = self._fallback_chains.get(capability, [])
        return [provider for _, provider in chain]

    async def get_with_fallback(self, capability: str) -> Any:
        chain = self.get_fallback_chain(capability)
        if not chain:
            raise KeyError(f"No provider registered for capability: {capability}")

        for provider in chain:
            if hasattr(provider, "is_available"):
                try:
                    available = await provider.is_available()
                    if available:
                        return provider
                except Exception:
                    continue
            else:
                return provider

        return chain[0]

    def swap(self, capability: str, new_provider: Any) -> None:
        self._providers[capability] = new_provider

    def list_providers(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for cap, p in self._providers.items():
            name = getattr(p, "provider_name", type(p).__name__)
            result[cap] = name
        return result

    def has(self, capability: str) -> bool:
        return capability in self._providers
