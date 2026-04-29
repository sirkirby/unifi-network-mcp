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

    def get(self, controller_id: str) -> Any | None:
        e = self._data.get(controller_id)
        if e is None:
            return None
        if time.time() - e.fetched_at > self._ttl:
            del self._data[controller_id]
            return None
        return e.payload

    def put(self, controller_id: str, payload: Any) -> None:
        self._data[controller_id] = _Entry(payload=payload, fetched_at=time.time())

    def invalidate(self, controller_id: str) -> None:
        self._data.pop(controller_id, None)
