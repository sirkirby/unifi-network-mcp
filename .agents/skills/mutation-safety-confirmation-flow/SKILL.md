---
name: myco:mutation-safety-confirmation-flow
description: |
  Covers the full implementation domain for adding and integrating mutating
  tools (create/update/delete) in the two-stage preview/execute safety flow.
  Applies when calling setup_permissioned_tool() at server init, declaring
  permission_category and permission_action on a new tool, using the
  unifi_core.confirmation helpers (preview_response, update_preview,
  toggle_preview, create_preview), or integrating a consumer. Also applies
  when debugging block behavior, interpreting preview responses, or reviewing
  PRs that touch the safety layer — even if the user doesn't explicitly ask
  about confirmation flow. Key files:
  packages/unifi-core/src/unifi_core/confirmation.py,
  packages/unifi-mcp-shared/src/unifi_mcp_shared/permissioned_tool.py.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Mutation Safety and Confirmation Flow

Every mutating tool (create/update/delete) routes through a two-stage preview/execute safety system. The first call returns a preview; a second call with `confirm=True` executes. This skill covers: wiring the permissioned decorator at server init, declaring permissions on tool functions, using the confirmation helpers correctly, reading preview responses on the consumer side, and distinguishing the two orthogonal safety axes.

The confirmation helpers live at `packages/unifi-core/src/unifi_core/confirmation.py` (NOT `unifi_mcp_shared` — only re-exported from there via `__init__.py`). The decorator wiring helper lives at `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissioned_tool.py`.

## Procedure A: Server-Level Setup with setup_permissioned_tool()

`setup_permissioned_tool()` is called **once at server init** — it replaces `server.tool` with the permissioned decorator. It is **not** called per-tool. All app context (category_map, server_prefix, logger, etc.) flows in as DI parameters. Never import app-level config inside `unifi-mcp-shared` or `unifi-core`.

```python
from unifi_mcp_shared.permissioned_tool import setup_permissioned_tool

# Called once at server init — replaces server.tool with the permissioned decorator
setup_permissioned_tool(
    server=server,
    category_map=category_map,           # e.g., {"network": "network", "devices": "device"}
    server_prefix=server_prefix,         # e.g., "NETWORK" — used for env var resolution
    register_tool_fn=register_tool,      # callback to add tool to tool_index
    diagnostics_enabled_fn=lambda: diag, # callable returning bool
    wrap_tool_fn=wrap_with_diagnostics,  # diagnostics wrapper
    logger=logger,
)
# After this call, @server.tool() IS the permissioned decorator
```

If you see `from app.settings import permission_mode` inside `unifi-mcp-shared` or `unifi-core`, that is a DI regression — report it and revert.

## Procedure B: Declare Permissions on a New Mutating Tool

After server setup, declare `permission_category` and `permission_action` as kwargs on `@server.tool()`. Both are required. Missing either causes the tool to bypass the safety layer silently (the decorator's fast path fires).

The tool function itself implements the preview/execute branching using helpers from `unifi_core.confirmation`:

```python
from unifi_core.confirmation import update_preview

@server.tool(
    name="update_network_config",
    description="Update a network configuration.",
    permission_category="network",
    permission_action="update",
)
async def update_network_config(
    network_id: str,
    confirm: bool = False,
    **kwargs,
) -> dict:
    if not confirm:
        current = await manager.get_network(network_id)
        return update_preview(
            resource_type="network",
            resource_id=network_id,
            resource_name=current.get("name"),
            current_state=current,
            updates=kwargs,
        )
    # confirm=True: re-fetch current state, merge, execute
    current = await manager.get_network(network_id)
    merged = {**current, **kwargs}
    return await manager.put_network(network_id, merged)
```

`confirm: bool = False` is mandatory on the function signature. The decorator injects `confirm=True` automatically in bypass mode by inspecting the signature — a missing parameter silently breaks bypass mode.

## Procedure C: Choosing and Using Confirmation Helpers

All helpers are in `packages/unifi-core/src/unifi_core/confirmation.py` and re-exported from `unifi_mcp_shared`:

| Helper | Use for | Key `preview` shape |
|---|---|---|
| `update_preview(resource_type, resource_id, resource_name, current_state, updates)` | Update operations | `{"current": {changed fields only}, "proposed": {delta}}` |
| `toggle_preview(resource_type, resource_id, resource_name, current_enabled)` | Enable/disable | `{"current": {"enabled": bool}, "proposed": {"enabled": !bool}}` |
| `create_preview(resource_type, resource_data, resource_name)` | Create operations | `{"will_create": {full payload}}` |
| `preview_response(action, resource_type, resource_id, current_state, proposed_changes)` | Custom / base | `{"current": {...}, "proposed": {...}}` |

All helpers return a response with the same envelope:

```json
{
  "success": true,
  "requires_confirmation": true,
  "action": "update",
  "resource_type": "network",
  "resource_id": "abc123",
  "preview": { "current": {...}, "proposed": {...} },
  "message": "Will update name on network 'abc123'. Set confirm=true to execute."
}
```

**Critical:** The key inside `preview` is `"proposed"` (not `"proposed_changes"`). Consumer code reading `response["preview"]["proposed_changes"]` returns `None` silently. This is the most common integration mistake with these helpers.

**`update_preview` filters `current_state`:** It automatically narrows `current_state` to only the keys being updated. This is intentional — reviewers see the before/after only for fields being changed, not the full resource.

**Why `success: true` in previews:** A preview is itself a successful operation. `success: true` means "the preview was built without error." It does NOT mean the mutation ran. Always check `requires_confirmation` to distinguish.

## Procedure D: Consumer-Side Preview Reading

Any MCP client or agent calling a mutating tool must handle the two-stage response:

```python
response = await call_tool("update_network_config", {
    "network_id": "abc123",
    "name": "new-name",
})

if response.get("requires_confirmation"):
    # First call returned a preview — nothing was changed.
    print("Current:", response["preview"]["current"])
    print("Proposed:", response["preview"]["proposed"])  # key is "proposed", not "proposed_changes"

    # User approves → re-invoke with confirm=True AND all original fields
    result = await call_tool("update_network_config", {
        "network_id": "abc123",
        "name": "new-name",   # must re-send delta fields
        "confirm": True,
    })
else:
    # Bypass mode or already confirmed.
    result = response
```

**Gotcha — silent preview trap:** Skipping the `requires_confirmation` check and treating a preview as completed (because `success` is `true`) means the change is never applied. The caller silently believes the operation succeeded. This is the most common consumer-side integration bug.

**Bypass mode:** When `UNIFI_TOOL_PERMISSION_MODE=bypass` (or `UNIFI_<SERVER>_TOOL_PERMISSION_MODE=bypass`), the decorator injects `confirm=True` before calling the function. The consumer pattern above handles both modes correctly without branching on mode.

**Incomplete second call:** The second call must include all original delta fields plus `confirm=True`. Sending only `{"confirm": True, "network_id": "abc123"}` produces empty kwargs — no change is applied and no error is raised.

## Procedure E: Permission Mode vs. Policy Gates — Orthogonal Axes

These two safety mechanisms are independent and must not be conflated.

| Axis | Controls | Configured via | Trigger behavior |
|---|---|---|---|
| **Permission mode** | Workflow (preview vs. immediate execute) | `UNIFI_TOOL_PERMISSION_MODE` / `UNIFI_<SERVER>_TOOL_PERMISSION_MODE` env var | `"confirm"` → two-stage; `"bypass"` → inject `confirm=True` |
| **Policy gates** | Hard on/off per tool | `PolicyGateChecker` / `category_map` config | Blocked tools return `{"success": False, "error": "..."}` on **any** call |

**Key rules:**

1. **Tools are always visible** — policy gates never hide a tool from the tool list. They block at call time. Callers see the tool, invoke it, and receive a denial error. Tool hiding would break capability negotiation.

2. **Gates fire on every call** — the policy gate check runs at the top of the `gated_func` wrapper, before any `confirm` branching. A gated tool returns an error on the first call (preview) AND the second call (confirm). There is no "preview-passes, gate-on-confirm" behavior.

3. **Mode and gates are independent** — `permission_mode=bypass` does not override a policy gate. A gated tool in bypass mode is still gated. "Bypassing the two-stage flow" ≠ "bypassing policy restrictions."

**Debugging guide:**

```
Tool returns error on first OR second call?
  → Check PolicyGateChecker config for the tool's category + action.
  → category_map and policy_gates come from the app layer, not unifi-core.

Tool executes immediately without preview?
  → Check UNIFI_TOOL_PERMISSION_MODE or UNIFI_<SERVER>_TOOL_PERMISSION_MODE.
  → "bypass" causes decorator to inject confirm=True before calling the function.

Tool blocked even in bypass mode?
  → Policy gate is active — check policy_gates config, not permission_mode.
```

## Cross-Cutting Gotchas

**1. `"proposed"` vs `"proposed_changes"`** — the key inside `preview` is `"proposed"` in all helpers. Consumer code reading `response["preview"]["proposed_changes"]` returns `None` silently.

**2. Missing `confirm` parameter** — every mutating tool must declare `confirm: bool = False`. Bypass injection inspects the function signature; if the param is missing, bypass mode silently fails to inject `confirm=True`.

**3. DI violation in shared packages** — `unifi-mcp-shared` and `unifi-core` must never import application-level config. All context flows in via `setup_permissioned_tool()`. If you see `from app.settings import ...` inside these packages, that is a regression.

**4. Incomplete second call** — must include all original delta fields plus `confirm=True`. Empty kwargs → empty merge → no change, no error.

**5. PR review gate** — every PR adding a mutating tool should be checked for: `permission_category` declared, `permission_action` declared, `confirm: bool = False` in signature, confirmation helper used on the `not confirm` path, second call re-fetches state before merging. See `community-pr-review` skill for the full checklist.
