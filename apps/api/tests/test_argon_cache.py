"""Argon2 verify cache tests."""

import time

from unifi_api.auth.cache import ArgonVerifyCache, CachedKey


def _make_cached(key_id: str = "k1", scopes: str = "read") -> CachedKey:
    return CachedKey(api_key_id=key_id, scopes=scopes, fetched_at=time.time())


def test_put_and_get_returns_value() -> None:
    cache = ArgonVerifyCache(max_size=4, ttl_seconds=60)
    cache.put("plaintext-1", _make_cached("k1"))
    hit = cache.get("plaintext-1")
    assert hit is not None and hit.api_key_id == "k1"


def test_miss_returns_none() -> None:
    cache = ArgonVerifyCache(max_size=4, ttl_seconds=60)
    assert cache.get("never-stored") is None


def test_ttl_expires() -> None:
    cache = ArgonVerifyCache(max_size=4, ttl_seconds=1)
    cache.put("p", _make_cached())
    time.sleep(1.2)
    assert cache.get("p") is None


def test_lru_eviction() -> None:
    cache = ArgonVerifyCache(max_size=2, ttl_seconds=60)
    cache.put("a", _make_cached("a"))
    cache.put("b", _make_cached("b"))
    cache.get("a")  # bump a to most-recent
    cache.put("c", _make_cached("c"))  # should evict b
    assert cache.get("a") is not None
    assert cache.get("b") is None
    assert cache.get("c") is not None


def test_invalidate_removes_by_key_id() -> None:
    cache = ArgonVerifyCache(max_size=4, ttl_seconds=60)
    cache.put("p1", _make_cached("k1"))
    cache.put("p2", _make_cached("k2"))
    cache.invalidate("k1")
    assert cache.get("p1") is None
    assert cache.get("p2") is not None
