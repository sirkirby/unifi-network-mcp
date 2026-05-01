---
name: myco:unifi-v2-get-by-id
description: |
  Activate this skill when implementing, fixing, or auditing any get_*_by_id method
  that uses ApiRequestV2 to call a UniFi V2 endpoint, even if the user doesn't explicitly
  ask about response shape handling. UniFi V2 single-resource GET endpoints return a list
  (not a dict like V1 endpoints), so an explicit list-unwrap step is mandatory. Covers:
  writing new V2 get_by_id methods, fixing existing ones with silent failures,
  auditing all V2 get_by_id methods for missing list-unwrap logic, and distinguishing
  V1 vs V2 response shapes when the version is ambiguous.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# UniFi V2 get_by_id Implementation

UniFi's V2 API returns single-resource GET responses as a **one-element list**, not a dict. V1 endpoints return a dict. Because the shapes differ by API version rather than resource type, every V2 `get_*_by_id` implementation must explicitly unwrap the list — omitting this produces a silent failure where an existing resource appears as "not found" with no exception or log noise.

Three production bugs shared this root cause: `get_acl_rule_by_id`, `get_client_group_by_id`, and `get_oon_policy_by_id` (all fixed in commit `30f6421`). Apply this skill proactively to any new V2 method.

## Prerequisites

- Confirm whether the endpoint is V1 or V2 — the signal is `ApiRequestV2` from `aiounifi.models.api`. V1 methods use plain dict-based requests; V2 methods construct an `ApiRequestV2` object.
- Understand the confirmed response shape: V2 returns `[{…}]`, V1 returns `{…}`
- The manager file already exists or is scaffolded at `packages/unifi-core/src/unifi_core/network/managers/<domain>_manager.py`

## Procedure A: Implement a New V2 get_by_id Method

1. **Import `ApiRequestV2`** at the top of the manager file:
   ```python
   from aiounifi.models.api import ApiRequestV2
   ```

2. **Call the V2 endpoint** and capture the raw response:
   ```python
   api_request = ApiRequestV2(method="get", path=f"/<resource-path>/{resource_id}")
   response = await self._connection.request(api_request)
   ```

3. **Unwrap using the two-branch pattern** — list branch first, dict branch second:
   ```python
   if isinstance(response, list) and response:
       return response[0]
   if isinstance(response, dict):
       return response
   return {"error": "not found"}
   ```

4. **Do not** write only the dict branch. The most common V2 shape is a list, and omitting the list check produces a silent failure — a valid resource returns `{"error": "not found"}` with no warning.

5. **Test both code paths**:
   - Pass a real ID → expect the resource dict returned
   - Pass a nonexistent ID → expect `{"error": "not found"}`, not an exception

### Complete method skeleton

```python
async def get_widget_by_id(self, widget_id: str) -> Dict[str, Any]:
    """Get a single widget by ID (V2 endpoint — response is a list, unwrap to dict)."""
    if not await self._connection.ensure_connected():
        raise ConnectionError("Not connected to controller")

    api_request = ApiRequestV2(method="get", path=f"/widgets/{widget_id}")
    try:
        response = await self._connection.request(api_request)
    except Exception:
        response = None

    if isinstance(response, list) and response:
        return response[0]
    if isinstance(response, dict):
        return response
    raise UniFiNotFoundError("widget", widget_id)
```

## Procedure B: Fix an Existing V2 get_by_id with a Silent Failure

When a `get_*_by_id` method returns nothing (or `{"error": "not found"}`) for a resource that actually exists, the root cause is almost always a missing list-unwrap.

1. **Locate the method** in `packages/unifi-core/src/unifi_core/network/managers/<domain>_manager.py`

2. **Identify the faulty pattern** — a dict-only check with no list branch:
   ```python
   # BROKEN — misses the V2 list shape entirely
   if isinstance(response, dict):
       return response
   return {"error": "not found"}
   ```

3. **Insert the list branch above the dict branch**:
   ```python
   # FIXED
   if isinstance(response, list) and response:
       return response[0]
   if isinstance(response, dict):
       return response
   return {"error": "not found"}
   ```

4. **Verify the method uses `ApiRequestV2`** — if it does, the response will be a list for V2 endpoints. If the method falls back to listing all resources and filtering by ID (the 405 workaround pattern used by `get_acl_rule_by_id`), the isinstance pattern does not apply; the list returned is the full collection, not the V2 single-resource wrapper.

5. **Confirm with a live or mock test** that the resource is returned correctly after the fix.

## Procedure C: Audit All V2 get_by_id Methods

Run this audit when onboarding to the codebase, after adding new tool files, or when a silent-failure regression is suspected.

1. **Find all get_by_id methods in the managers directory**:
   ```bash
   grep -rn "def get_.*_by_id" packages/unifi-core/src/
   ```

2. **Identify which ones use ApiRequestV2 (V2 endpoints)**:
   ```bash
   grep -B 30 "def get_.*_by_id" packages/unifi-core/src/ -r | grep "ApiRequestV2"
   ```

3. **Check each V2 method for the list-unwrap branch**:
   ```bash
   grep -A 20 "def get_.*_by_id" packages/unifi-core/src/ -r | grep "isinstance.*list"
   ```
   A V2 method with no matching result is at risk.

4. **Fix each at-risk method** using Procedure B above.

5. **Commit with a clear message** referencing the pattern, e.g.:
   ```
   fix: add V2 list-unwrap to get_by_id methods (client_group, oon_policy)
   ```

## Cross-Cutting Gotchas

**Silent failure with no signal** — Checking only `isinstance(response, dict)` when V2 returns a list causes the method to fall through to `{"error": "not found"}`. There is no exception, no log noise — just a wrong result. This is why the bug survived undetected until explicit testing.

**Empty list means not found** — V2 may return `[]` for a nonexistent resource ID. The guard `response[0] if response else {"error": "not found"}` (or `and response` in the condition) handles this safely without raising an `IndexError`.

**Branch order is load-bearing** — The list check must come before the dict check. A list is never a dict, so the order doesn't cause logical overlap, but accidentally reversing the branches in a future edit would silently reintroduce the bug.

**V1 vs V2 determination** — The canonical signal is `ApiRequestV2` usage, not the URL path. If the manager imports and uses `ApiRequestV2(method="get", ...)`, the endpoint is V2 and the response will be a list. Plain dict-based V1 requests return a dict directly.

**The 405 workaround pattern is different** — `get_acl_rule_by_id` in `acl_manager.py` does not use `ApiRequestV2` for the by-ID call because `GET /acl-rules/{id}` returns 405. Instead it calls `get_acl_rules()` (which returns the full list) and filters by ID. Do not apply the V2 isinstance pattern to 405-workaround methods.
