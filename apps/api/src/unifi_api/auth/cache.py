"""Argon2 verify cache.

Bounded LRU keyed by SHA-256(plaintext_token), value = (api_key_id, scopes,
fetched_at). Cache hit lets the auth path skip ~50-100ms argon2id verify.

Process-global singleton initialized in server.create_app and wired into
app.state. NOT an asyncio.Lock-guarded structure - Python dict + collections.OrderedDict
gives us O(1) LRU and our access pattern is single-process, lock-free safe under CPython
GIL for these atomic operations. If we move to a multi-process deployment later, this
becomes a Redis cache with the same interface.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class CachedKey:
    api_key_id: str
    scopes: str
    fetched_at: float


def _hash_plaintext(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class ArgonVerifyCache:
    def __init__(self, max_size: int = 1024, ttl_seconds: int = 60) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._data: OrderedDict[str, CachedKey] = OrderedDict()

    def get(self, plaintext: str) -> CachedKey | None:
        h = _hash_plaintext(plaintext)
        entry = self._data.get(h)
        if entry is None:
            return None
        if time.time() - entry.fetched_at > self._ttl:
            del self._data[h]
            return None
        self._data.move_to_end(h)
        return entry

    def put(self, plaintext: str, value: CachedKey) -> None:
        h = _hash_plaintext(plaintext)
        self._data[h] = value
        self._data.move_to_end(h)
        while len(self._data) > self._max_size:
            self._data.popitem(last=False)

    def invalidate(self, api_key_id: str) -> None:
        """Drop all entries whose api_key_id matches."""
        to_remove = [h for h, v in self._data.items() if v.api_key_id == api_key_id]
        for h in to_remove:
            del self._data[h]
