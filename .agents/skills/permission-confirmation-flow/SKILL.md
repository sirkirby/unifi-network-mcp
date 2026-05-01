---
name: myco:permission-confirmation-flow
description: |
  Apply this skill whenever implementing a new mutating tool (create, update,
  delete) in unifi-mcp, reviewing a PR that touches the permission system, or
  debugging confirmation/preview flow behavior — even if the user doesn't
  explicitly ask about permissions. Covers the two-axis permission model (runtime
  mode vs. config-time policy gates), wiring permission_category and
  permission_action as decorator kwargs via @server.tool(), implementing the
  preview-then-confirm contract correctly, understanding that preview shows the
  delta not the merged result, preserving the double-fetch at confirm time to
  prevent TOCTOU races, and test isolation via decorator replacement in runtime.py
  vs. main.py.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Permission & Confirmation Flow Architecture

Every mutating tool in unifi-mcp participates in a two-axis permission system
defined in `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissioned_tool.py`.
The two axes are orthogonal and must not be conflated. Every new tool author and
every PR reviewer must understand both axes and the preview-then-confirm contract
before touching mutating tools.

## Prerequisites

- Shared package is installed or editable-linked (`packages/unifi-mcp-shared`)
- The tool module will be imported in `main.py` so the decorator chain is wired
  before the server starts
- For new tool authors: read at least one existing mutating tool for reference
  (e.g., `apps/network/src/unifi_network_mcp/tools/devices.py`, any `@server.tool`
  block with `permission_category`)

## Procedure A: Understand the Two-Axis Model Before Touching Anything

The permission system has exactly two independent axes. Conflating them causes
architectural errors and incorrect PR review feedback.

**Axis 1 — Permission mode (caller-controlled, runtime)**

The caller passes `permission_mode` at invocation time:

- `confirm` (default): the tool enters preview mode on first call; the caller
  must re-invoke with `confirm=True` to execute the mutation.
- `bypass`: skip the preview step and execute immediately. Only permitted when
  the admin has granted bypass for this tool category in the server config.

This axis is dynamic — the same tool behaves differently depending on what the
caller passes. It is NOT a configuration-time setting.

**Axis 2 — Policy gates (admin-controlled, config-time)**

Each tool category has a policy gate that is either enabled or disabled by the
administrator in the server configuration. A disabled gate blocks execution for
all callers regardless of `permission_mode`.

Key invariant: **tools are always registered and visible regardless of policy
gates.** The gate blocks at *execution time*, not at *registration time*. Never
assume a tool appearing in the MCP tool list is unrestricted — it may be gated
off. Agents must not treat tool visibility as a proxy for permission.

## Procedure B: Wire permission_category and permission_action into a New Tool

Every new mutating tool declares its permission category and action as **decorator
kwargs** passed to `@server.tool(...)`. These are NOT function parameters.

1. **Pass `permission_category` and `permission_action` in the `@server.tool` decorator call:**

   ```python
   @server.tool(
       name="unifi_update_my_resource",
       description="Update a resource",
       permission_category="your_category",  # e.g. "network", "firewall", "devices", "dns"
       permission_action="update",           # "update", "create", or "delete"
       annotations=ToolAnnotations(readOnlyHint=False, ...),
   )
   async def update_my_resource(
       resource_id: str,
       confirm: bool = False,
       ...
   ) -> Dict[str, Any]:
       ...
   ```

   At runtime, `server.tool` is the permissioned decorator installed by
   `setup_permissioned_tool()` in `main.py`. It intercepts `permission_category`
   and `permission_action` from the decorator's own kwargs — they are NOT
   forwarded to the function body and must NOT appear in the function signature.

2. **`confirm: bool = False` is the only permission-related function parameter.**
   It controls which branch (preview vs. execute) the function takes. See
   Procedure C for correct branching.

3. **Choose the correct `category`:** Category strings map to admin-configured
   policy gates. Use the same string as other tools in the same domain (all DNS
   tools share one category, all device tools share another). Check existing
   tools in the same module for the canonical string — e.g., `"devices"` in
   `tools/devices.py`, `"client_group"` in `tools/client_groups.py`.

4. **`setup_permissioned_tool()` is called once in `main.py` at module load** —
   it installs the permission-aware decorator onto `server.tool` for the entire
   server. You never call it per-tool. Signature:

   ```python
   # apps/network/src/unifi_network_mcp/main.py
   setup_permissioned_tool(
       server=server,
       category_map=NETWORK_CATEGORY_MAP,
       server_prefix="network",
       register_tool_fn=register_tool,
       diagnostics_enabled_fn=diagnostics_enabled,
       wrap_tool_fn=wrap_tool,
       logger=logger,
   )
   ```

   No special wiring in `main.py` is needed for individual tools beyond importing
   the tool module so the `@server.tool(...)` decorator fires at import time.

## Procedure C: Implement the Preview-Then-Confirm Flow Correctly

The confirmation flow is a two-step state machine. Both steps must be handled.
Use the helper functions in `packages/unifi-core/src/unifi_core/confirmation.py`
(`preview_response`, `update_preview`, `create_preview`, `toggle_preview`) rather
than building preview dicts by hand.

**Step 1 — Preview call (first invocation, `confirm=False`):**

```python
from unifi_core.confirmation import update_preview

async def update_my_resource(..., confirm: bool = False) -> Dict[str, Any]:
    if not confirm:
        current = await manager.get(resource_id)
        return update_preview(
            resource_type="my_resource",
            resource_id=resource_id,
            resource_name=current.get("name"),
            current_state=current,
            updates=updates,
        )
    # confirm=True path below
```

The helper returns:

```python
{
    "success": True,               # NOT a completion signal — see gotcha below
    "requires_confirmation": True,
    "action": "update",
    "resource_type": "my_resource",
    "resource_id": "...",
    "preview": {
        "current": { ... },        # current values of fields being changed
        "proposed": { ... },       # caller's intended changes (the delta)
    },
    "message": "Will update ... Set confirm=true to execute.",
}
```

The correct agent/caller behavior:

```python
response = await call_tool("update_my_resource", args)
if response.get("requires_confirmation"):
    # Show response["preview"] to the user for review
    # On user approval, re-invoke with confirm=True
    response = await call_tool("update_my_resource", {**args, "confirm": True})
```

**`success: True` in a preview response does NOT mean the mutation completed.**
It means the preview was generated successfully. Checking only `success` and
treating it as completion silently drops the confirmation step — this is a real
risk for any new agent integration.

**Step 2 — Confirm call (`confirm=True`):**

Re-invoke with `confirm=True`. The tool executes the mutation:

```python
{
    "success": True,
    "requires_confirmation": False,
    "result": { ... },             # post-mutation state
}
```

`success: True` AND `requires_confirmation: False` (or absent) together confirm
completion.

## Procedure D: Understand Preview Semantics — Delta, Not Merged Result

The `preview.proposed` block returned in step 1 shows **the caller's partial update
intent (the delta)**, not the deep-merged final object that will be written to the
device.

Example: caller sends `{"vlan_id": 10}` as the update payload → `preview.proposed`
shows `{"vlan_id": 10}`, and `preview.current` shows the current value of `vlan_id`
only. The full config is not shown.

The executor applies `deep_merge(current_state, delta)` (from
`unifi_core.merge.deep_merge`) at confirm time against a freshly fetched current
state (see Procedure E). The preview is a fidelity check on what the caller intends
to change, not a simulation of the final API payload.

**PR review implication:** Do not flag a preview as incomplete because it doesn't
show the full merged config. A reviewer asking "why doesn't the preview show the
final merged object?" is applying the wrong model. The delta-preview design is
correct and intentional.

If you need to inspect the merged result in a debug or test context, call
`deep_merge(current_state, delta)` yourself — import from `unifi_core.merge`.
The preview pathway does not expose this.

## Procedure E: Preserve the Double-Fetch at Confirm Time

When `confirm=True`, the tool **re-fetches the current state from the API** before
merging and writing. This appears redundant if you only see the code path. It is not.

**Why it must stay — TOCTOU prevention:**

The preview call (step 1) fetched state₁ to generate the delta preview. By the
time the confirm call (step 2) arrives, the device may have changed (another
admin, another tool, a background sync). Reusing the step-1 fetch would merge
the delta against a stale base:

```
Step 1: fetch state₁ → show delta preview
   ... time passes, another change lands ...
Step 2 (confirm): re-fetch state₂ → deep_merge(state₂, delta) → write ✓
```

Without the re-fetch, step 2 would use state₁ as the merge base — classic
time-of-check/time-of-use race, silently overwriting the intervening change.

**Do not optimize this away.** If a reviewer or profiler flags the double-fetch
as a redundant API call, explain the TOCTOU rationale. It is a correctness
requirement, not an oversight.

## Procedure F: Test Isolation via Decorator Replacement

The full permission enforcement chain is only wired in the live server via
`main.py`. The `runtime.py` module installs a lightweight wrapper
(`_create_permissioned_tool_wrapper`) that strips `permission_category`,
`permission_action`, and `auth` kwargs before passing through to FastMCP — it
does not enforce policy gates or run the preview/confirm state machine.

**What this means in practice:**

- Unit tests that import the tool function directly (not via the MCP server)
  bypass the policy gate and the two-step state machine. This is intentional —
  it lets tests exercise tool logic in isolation without needing a full server
  context.
- The `runtime.py` wrapper pops `permission_category`/`permission_action` from
  the **decorator's** kwargs before they reach FastMCP. The function signature
  never has these params — this is expected behavior, not a bug.
- To test the full permission/confirmation flow end-to-end, use integration tests
  that invoke through the live MCP server stack (not direct function import).

**Do not put permission logic inside the function body.** Permission routing
belongs in the decorator layer (`permissioned_tool.py`), not in individual tool
functions. Any branching on `permission_category` inside a tool function will
never see those values — they are consumed by the decorator layer before the
function body runs.

## Cross-Cutting Gotchas

**`success: True` is ambiguous — always check `requires_confirmation` first.**
Preview responses set `success: True` to signal successful preview generation,
not a completed mutation. Any agent code that reads only `success` will silently
skip the confirmation prompt and falsely believe the mutation succeeded.

**Tool visibility ≠ permission.** A tool appearing in the MCP tool list does not
mean it is unrestricted. Policy gates block at execution time. Never infer from
tool visibility that a call will succeed.

**The preview shows the delta, not the merged result.** The correct question
when reviewing a preview is "does this show what the caller intends to change?"
not "does this match what the API will receive?"

**Double-fetch is TOCTOU prevention, not waste.** Eliminating the re-fetch at
confirm time introduces a silent correctness bug whenever state changes between
the preview and confirm calls.

**`permission_category`/`permission_action` belong in the decorator call, not
the function signature.** Adding them to the function signature is wrong —
they're consumed at decoration time, before the function body is ever called.
