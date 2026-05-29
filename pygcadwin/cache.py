"""Attribute caching proxy for expensive COM objects."""

from __future__ import annotations

from typing import Any


class Cached:
    """Proxy that caches attribute reads and writes on another object."""

    def __init__(self, instance: Any):
        object.__setattr__(self, "_instance", instance)
        object.__setattr__(self, "_is_enabled", True)
        object.__setattr__(self, "_storage", {})

    def get_original(self) -> Any:
        """Return the wrapped object."""
        return self._instance

    def switch_caching(self, is_enabled: bool) -> None:
        """Enable or disable caching; disabling also clears cached values."""
        object.__setattr__(self, "_is_enabled", bool(is_enabled))
        if not is_enabled:
            object.__setattr__(self, "_storage", {})

    def __getattr__(self, key: str) -> Any:
        storage = object.__getattribute__(self, "_storage")
        if object.__getattribute__(self, "_is_enabled") and key in storage:
            return storage[key]
        value = getattr(object.__getattribute__(self, "_instance"), key)
        if object.__getattribute__(self, "_is_enabled"):
            storage[key] = value
        return value

    def __setattr__(self, key: str, value: Any) -> None:
        if key in {"_instance", "_is_enabled", "_storage"}:
            object.__setattr__(self, key, value)
            return
        setattr(object.__getattribute__(self, "_instance"), key, value)
        if object.__getattribute__(self, "_is_enabled"):
            object.__getattribute__(self, "_storage")[key] = value

    def __delattr__(self, key: str) -> None:
        if key in {"_instance", "_is_enabled", "_storage"}:
            object.__delattr__(self, key)
            return
        storage = object.__getattribute__(self, "_storage")
        storage.pop(key, None)
        delattr(object.__getattribute__(self, "_instance"), key)

