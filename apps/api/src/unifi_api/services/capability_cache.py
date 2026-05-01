"""Capability payload cache. TTL-bounded, keyed by controller_id."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    payload: Any
    fetched_at: float


class CapabilityCache:
    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, _Entry] = {}
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total) if total else 0.0

    def get(self, controller_id: str) -> Any | None:
        e = self._data.get(controller_id)
        if e is None:
            self._misses += 1
            return None
        if time.time() - e.fetched_at > self._ttl:
            del self._data[controller_id]
            self._misses += 1
            return None
        self._hits += 1
        return e.payload

    def put(self, controller_id: str, payload: Any) -> None:
        self._data[controller_id] = _Entry(payload=payload, fetched_at=time.time())

    def invalidate(self, controller_id: str) -> None:
        self._data.pop(controller_id, None)
