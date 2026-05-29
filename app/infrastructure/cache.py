"""Implementación de caché en memoria con TTL.

En producción se sustituye por Redis (misma interfaz ICache — LSP/DIP).
Resuelve el soporte de caché para MH-03 y la invalidación del Observer.
"""
from __future__ import annotations

import time

from app.repositories.interfaces import ICache


class InMemoryCache(ICache):
    def __init__(self) -> None:
        self._store: dict[str, tuple[dict, float]] = {}

    def get(self, key: str) -> dict | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: dict, ttl: int = 60) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
