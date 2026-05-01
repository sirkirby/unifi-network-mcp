"""CI gate: deep query produces constant manager call count regardless of
result cardinality.

PR1 baseline: only the smoke `health` field exists, so this gate just
asserts the framework (`RequestCache` dedupe within one request) is wired
correctly. PR2/3/4 add real deep-query call-count assertions once
network/protect/access resolvers exist.
"""

import asyncio

import pytest

from unifi_api.graphql.context import RequestCache


@pytest.mark.asyncio
async def test_request_cache_dedupes_within_one_query() -> None:
    """Two resolvers in one query reaching the same manager call share one fetch.

    Constructed at PR1 against the RequestCache directly. PR2 augments this
    with a real deep-query call-count test once network resolvers exist.
    """
    cache = RequestCache()
    fetches = 0

    async def _fetch():
        nonlocal fetches
        fetches += 1
        return ["client_a", "client_b", "client_c"]

    a, b = await asyncio.gather(
        cache.get_or_fetch("network/clients/cid1", _fetch),
        cache.get_or_fetch("network/clients/cid1", _fetch),
    )
    assert a == b
    assert fetches == 1, "RequestCache failed to dedupe — N+1 risk"
