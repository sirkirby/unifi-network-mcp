---
name: myco:extend-unifi-api
description: |
  Apply this skill when working on apps/api/ — adding serializers for new
  tool/resource pairs, implementing resource endpoints, wiring multi-controller
  factory managers, designing pagination for new list endpoints, or choosing
  error contracts. Covers: decorator-based serializer registration in
  apps/api/src/unifi_api/serializers/<domain>/<resource>.py; cursor-based
  pagination via the module-level paginate() function and Cursor class;
  render-hint kind conventions and forward-compatible optional extensions;
  HTTP 409 vs 200-envelope error contracts for resource vs action endpoints;
  ManagerFactory class for multi-controller concurrency; apps/api dependency
  rule (unifi-core only); serializer coverage gate phases; and release tag
  policy. Activate even when the user hasn't explicitly asked about serializers
  or pagination — any PR touching apps/api/ should follow these patterns.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Extending the unifi-api REST Platform

`apps/api/` is the non-MCP HTTP delivery channel for UniFi controller data —
the substrate for future app consumers (Pi extension, dashboards, Electron
desktop). It is **not** an MCP server; its patterns, serializers, pagination,
and error contracts are distinct from the MCP layer and must stay that way.

This skill covers everything needed when adding or modifying a resource in
`apps/api/`: writing a serializer, paginating a list endpoint, setting render
hints, choosing the right error contract, wiring factory managers for
multi-controller concurrency, and staying within the dependency rules.

## Prerequisites

- `unifi-core` already has the manager method for the resource (or you've
  added one following the existing manager patterns).
- The MCP tool function already exists (or is being added in the same PR).
- You are working in `apps/api/src/unifi_api/` — not in `apps/network/`,
  `apps/protect/`, or `apps/access/`.
- **Dependency rule:** `apps/api/` may only import from `unifi-core`. It must
  NOT import from `unifi-mcp-shared` (that package is for MCP servers only).
  Violating this creates circular imports.

## Procedure A: Adding a Serializer for a New Tool/Resource

Every tool/resource pair exposed through the API needs a serializer. The
serializer lives in the API domain — not in `unifi-core` — because it encodes
an HTTP-API representation contract, not domain logic.

**1. Create the module** at the correct path:

```
apps/api/src/unifi_api/serializers/<domain>/<resource>.py
```

Domain is one of `network`, `protect`, `access`. Resource matches the tool
family (e.g., `clients`, `cameras`, `doors`).

**2. Write the serializer class:**

```python
# apps/api/src/unifi_api/serializers/network/clients.py
from unifi_api.serializers._base import RenderKind, Serializer, register_serializer

@register_serializer(
    tools=["unifi_list_clients", "unifi_get_client"],
    resources=[("network", "clients")],
)
class ClientSerializer(Serializer):
    kind = RenderKind.LIST  # required — see Procedure C for kind choices

    # Optional render-hint extensions (declare only what consumers need):
    primary_key = "mac"
    display_columns = ["hostname", "ip", "status", "last_seen"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "mac": obj.raw.get("mac"),
            "ip": obj.raw.get("last_ip"),
            "hostname": obj.raw.get("hostname"),
            "status": obj.raw.get("state"),
            "last_seen": obj.raw.get("last_seen"),
        }
```

The `tools` argument accepts either a bare list of tool names (serializer's
class-level `kind` applies to all) or a `dict[str, {"kind": RenderKind}]` for
per-tool kind overrides. The `resources` argument uses the same two forms with
`(product, resource_path)` tuples as keys.

**3. The registry picks it up automatically.** At service startup,
`_registry.py` walks `serializers/` and imports all modules. Broken
serializers fail loud at startup — never silently at request time. No central
manifest entry needed; the decorator declares ownership.

**4. The action endpoint dispatches via serializers.** The action endpoint flow:

> resolve tool → invoke manager method → look up serializer from registry →
> call `serializer.serialize_action(result, tool_name=tool_name)` → return
> structured response

**5. Resource endpoints reuse the same serializer.** `POST /v1/actions/unifi_list_clients`
and `GET /v1/sites/{id}/clients` must produce byte-identical response shapes —
both dispatch through `ClientSerializer`.

**Directory layout for reference:**

```
apps/api/src/unifi_api/serializers/
├── __init__.py          # registry + decorators
├── _base.py             # Serializer base class + RenderKind + register_serializer
├── _registry.py         # auto-discovery walker + validate_manifest
├── network/
│   ├── clients.py
│   ├── devices.py
│   ├── networks.py
│   ├── firewall_rules.py
│   └── wlans.py
├── protect/
│   ├── cameras.py
│   └── events.py
└── access/
    ├── doors.py
    ├── users.py
    └── credentials.py
```

## Procedure B: Implementing Cursor-Based Pagination

Resource list endpoints use cursor-based pagination — not offset-based.
Offset pagination skips or duplicates rows under concurrent inserts; cursor
pagination is stable because it keys off the last-seen `(ts, id)` tuple.

**Endpoint signature:**

```
GET /v1/sites/{id}/clients?limit=50&cursor=<opaque>
```

**Response envelope** (every list endpoint returns this shape):

```json
{
  "items": [ /* up to limit objects */ ],
  "next_cursor": "eyJsYXN0X2lkIjogImFiYzEyMyIsICJsYXN0X3RzIjogMTcyNzc0ODkwMH0="
}
```

The cursor is an opaque base64-encoded `{last_id, last_ts}`. Consumers detect
end-of-list when `next_cursor` is `null`. Do NOT include `total_count` — it
requires a full table scan and is stale under concurrency.

**Using the pagination helpers** (`services/pagination.py`):

```python
from unifi_api.services.pagination import Cursor, InvalidCursor, paginate

# Decode incoming cursor (if any)
cursor: Cursor | None = None
if cursor_param:
    try:
        cursor = Cursor.decode(cursor_param)
    except InvalidCursor:
        raise HTTPException(
            status_code=400,
            detail={"kind": "invalid_cursor", "message": "cursor position has been deleted"},
        )

# Fetch full snapshot from the manager (pagination is applied in-memory)
items = await client_manager.get_clients()

# Apply pagination: returns (page, next_cursor_or_None)
page, next_cursor = paginate(
    items,
    limit=limit,
    cursor=cursor,
    key_fn=lambda item: (item.raw.get("last_seen", 0), item.raw.get("_id", "")),
)

return {
    "items": [serializer.serialize(item) for item in page],
    "next_cursor": next_cursor.encode() if next_cursor else None,
}
```

`paginate()` is a **module-level function** — not a class method. It takes:
- `items`: the full unsorted snapshot from the manager
- `limit`: page size (keyword-only)
- `cursor`: decoded `Cursor` or `None` (keyword-only)
- `key_fn`: callable returning `(ts, id)` for each item (keyword-only)

It returns `(page: list, next_cursor: Cursor | None)`. The `Cursor` class
handles base64 encoding/decoding; call `.encode()` to produce the opaque
string for the response.

**Constraints:**

- `limit` default: 50; max: 200. Reject higher values with `400 Bad Request`.
- UniFi managers return full snapshots — pagination is applied in-memory after
  the manager call, not via per-page controller round-trips.

## Procedure C: Designing Render Hints

Every serializer declares a `kind` string. This is the minimum required
contract. Optional metadata fields are additive — declare them only when a
specific consumer needs them.

**Seed kinds** (use `RenderKind` enum values from `_base.py`):

| `RenderKind`  | When to use                                           |
|---------------|-------------------------------------------------------|
| `LIST`        | Flat collection (clients, devices, rules)             |
| `DETAIL`      | Single entity with full fields                        |
| `DIFF`        | Structured change delta (mutation preview)            |
| `TIMESERIES`  | Time-indexed data (uptime, event graphs)              |
| `EVENT_LOG`   | Log entries with timestamps                           |
| `EMPTY`       | Success with no output (config write, delete)         |
| `STREAM`      | Streaming data (camera streams, live feeds)           |

**Minimum — every serializer must have this:**

```python
class MySerializer(Serializer):
    kind = RenderKind.LIST  # required
```

**Optional extensions — declare only what downstream renderers need:**

```python
class MySerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "mac"                                       # optional
    display_columns = ["hostname", "ip", "status"]            # optional
    sort_default = "last_seen"                                # optional
```

Clients that don't understand optional fields ignore them — no breaking change.
Do not add field-schema metadata (sortable/filterable flags, enum values) until
post-Phase 3; `kind` alone is sufficient for v1 rendering.

**The `/v1/catalog/tools` endpoint** surfaces whatever the serializer declares:

```json
{
  "name": "unifi_list_clients",
  "render_hint": {
    "kind": "list",
    "primary_key": "mac",
    "display_columns": ["hostname", "ip", "status", "last_seen"]
  }
}
```

## Procedure D: Resource Endpoints vs. Action Endpoints — Error Contracts

These two endpoint families follow different error conventions. Don't mix them.

**Resource endpoints** (`GET /v1/sites/{id}/{resource}`) follow REST convention:
HTTP status code signals success; body provides detail.

| Situation                        | Status | Body                                                          |
|----------------------------------|--------|---------------------------------------------------------------|
| Success                          | 200    | `{"items": [...], "next_cursor": ...}`                        |
| Controller lacks required product| **409**| `{"kind": "capability_mismatch", "missing_product": "protect", "message": "..."}` |
| Invalid cursor                   | 400    | `{"kind": "invalid_cursor", "message": "..."}`                |
| limit > 200                      | 400    | standard validation error                                     |

Why 409 for capability mismatch (not 404, not 200):
- Not 404: the endpoint path is valid; the issue is controller state.
- Not 200: a GET that can't return the resource is a 4xx, not a success.
- 409 "conflicts with server state" is accurate: the controller doesn't have
  the required product.

```
GET /v1/sites/default/cameras?controller=xyz
→ HTTP 409 Conflict
{"kind": "capability_mismatch", "missing_product": "protect",
 "message": "Controller does not support the Protect product"}
```

Checks are per-resource and independent: `/cameras` requires Protect,
`/clients` requires Network.

**Action endpoints** (`POST /v1/actions/{tool_name}`) follow MCP convention:
always return HTTP 200; surface errors in the envelope.

```json
POST /v1/actions/unifi_list_cameras
→ HTTP 200
{"success": false, "error": "Cameras product not available"}
```

**Client handling pattern:** switch on `status === 409` before parsing body;
use `kind === "capability_mismatch"` to distinguish from ETag conflicts on
mutations.

## Procedure E: Wiring the Multi-Controller Factory

`unifi-api` serves multiple concurrent controller sessions in one process, so
the MCP-style global singleton factories don't work here. The implementation
uses `ManagerFactory` — a manual async-aware cache (explicitly **not**
`@lru_cache`, because async values and per-call session args make `@lru_cache`
the wrong tool).

**All factory logic lives in one module:**

```
apps/api/src/unifi_api/services/managers.py
```

**Accessing managers in routes** — the factory is wired into `app.state`
during lifespan; routes access it there:

```python
from unifi_api.services.managers import ManagerFactory

# In a route handler:
factory: ManagerFactory = request.app.state.manager_factory

# Get a connection manager for a specific controller + product:
cm = await factory.get_connection_manager(session, controller_id, "network")

# Get a named domain manager (attr_name matches the manager class name in the
# product builder dict, e.g. "client_manager", "firewall_manager"):
client_mgr = await factory.get_domain_manager(
    session, controller_id, "network", "client_manager"
)
```

`ManagerFactory` uses `asyncio.Lock` per `controller_id` around construction
to prevent concurrent-cache-miss races. Cache lives at the connection layer
because that's where aiohttp session state lives; manager construction is
cheap (just stores a reference to the `ConnectionManager`).

**Cache invalidation** — on controller delete or credentials update:

```python
await factory.invalidate_controller(controller_id)
```

This evicts all cached `ConnectionManager` and domain manager instances for
that controller.

**`unifi-core` needs zero changes** for this pattern. Existing managers
already support per-controller instantiation; `ManagerFactory` layers the
async-safe caching on top.

## Cross-Cutting Gotchas

**Dependency rule — never import `unifi-mcp-shared` from `apps/api/`.**
`unifi-mcp-shared` contains validator schemas for MCP servers. Importing it
from `apps/api/` creates circular imports and couples two unrelated delivery
channels. The correct dependency chain is: `apps/api/` → `unifi-core` only.

**Serializer coverage gates — Phase 3 is permissive, Phase 4 is strict.**
Phase 3 ships with `discover_serializers(set())` at lifespan startup; tools
without serializers get `{"kind": "empty"}` in `/v1/catalog/tools`. Phase 4
flips to `discover_serializers(set(manifest.all_tools()))` and adds a CI
assertion that runs `validate_manifest` at startup. From that commit on, any
new tool added without a serializer fails CI. Do not auto-register a
`DefaultSerializer` as a workaround — it hides the missing-serializer signal
and makes catalog render hints useless.

**Release tag policy — no `api/*` tags until Phase 7.**
Phases 0–6 are internal development only. The first consumer-facing tag is
`api/v0.1.0` (Phase 7), paired with a GHCR Docker image, docs, and release
notes. Do not cut partial release tags; they create support burden before the
full surface (controllers, resources, streams, admin UI, codegen, SDKs) is
ready.

**Single PR per phase.**
Phases 0–2 each landed as a single PR despite comparable scope (Phase 0: 17
commits, 162 files; Phase 2: 19 commits, ~3000 LOC). Phase 3 follows the same
pattern. Splitting into sub-PRs creates incoherent transitional states with no
shipping value to justify the overhead.

**New tool category contribution checklist** (extends `add-tool-category`):
1. Manager method in `unifi-core` — shared, already required
2. MCP tool function in `apps/<domain>/` — already required
3. **API serializer** in `apps/api/src/unifi_api/serializers/<domain>/<resource>.py` — NEW, required for Phase 4+ CI gate
