from __future__ import annotations
from typing import Any, Callable


class ModelRegistry:
    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, list[str]] = {}
        self._transformers: dict[str, dict[tuple[str, str], Callable[[Any], Any]]] = {}

    def register(self, name: str, schema: dict[str, Any], version: str) -> None:
        if name not in self._schemas:
            self._schemas[name] = {}
            self._versions[name] = []
        self._schemas[name][version] = schema
        if version not in self._versions[name]:
            self._versions[name].append(version)

    def get_schema(self, name: str, version: str = "latest") -> dict[str, Any]:
        if name not in self._schemas:
            raise KeyError(f"No schema registered for '{name}'")
        if version == "latest":
            latest_version = self._versions[name][-1]
            return self._schemas[name][latest_version]
        if version not in self._schemas[name]:
            raise KeyError(f"No version '{version}' for schema '{name}'")
        return self._schemas[name][version]

    def register_transformer(
        self,
        name: str,
        from_version: str,
        to_version: str,
        fn: Callable[[Any], Any],
    ) -> None:
        if name not in self._transformers:
            self._transformers[name] = {}
        self._transformers[name][(from_version, to_version)] = fn

    def transform(
        self,
        name: str,
        data: Any,
        from_version: str,
        to_version: str,
    ) -> Any:
        if name not in self._transformers:
            raise KeyError(f"No transformers registered for '{name}'")
        key = (from_version, to_version)
        if key not in self._transformers[name]:
            raise KeyError(
                f"No transformer from '{from_version}' to '{to_version}' for '{name}'"
            )
        return self._transformers[name][key](data)
