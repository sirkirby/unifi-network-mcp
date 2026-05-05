---
name: myco:mutation-safety-confirmation-flow
description: |
  Covers the full implementation domain for adding and integrating mutating
  tools (create/update/delete) in the two-stage preview/execute safety flow.
  Applies when calling setup_permissioned_tool() at server init, declaring
  permission_category and permission_action on a new tool, using the
  unifi_core.confirmation helpers (preview_response, update_preview,
  toggle_preview, create_preview), or integrating a consumer. Also applies
  when debugging confirmation behavior, interpreting preview responses,
  handling test isolation via decorator replacement in runtime.py vs.
  main.py, or reviewing PRs that touch the safety layer — even if the user
  doesn't explicitly ask about confirmation flow. Covers the two-axis
  permission model (runtime mode vs. config-time policy gates), preview
  semantics (delta not merged result), TOCTOU prevention via double-fetch,
  and test isolation patterns. Key files:
  packages/unifi-core/src/unifi_core/confirmation.py,
  packages/unifi-mcp-shared/src/unifi_mcp_shared/permissioned_tool.py.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Mutation Safety and Confirmation Flow

Every mutating tool (create/update/delete) routes through a two-stage preview/execute safety system. The first call returns a preview; a second call with `confirm=True` executes. This skill covers: the two-axis permission model (runtime mode vs. config-time policy gates), wiring the permissioned decorator at server init, declaring permissions on tool functions, using the confirmation helpers correctly, reading preview responses on the consumer side, understanding preview semantics, TOCTOU prevention via double-fetch, and test isolation patterns.

The confirmation helpers live at `packages/unifi-core/src/unifi_core/confirmation.py` (NOT `unifi_mcp_shared` — only re-exported from there via `__init__.py`). The decorator wiring helper lives at `packages/unifi-mcp-shared/src/unifi_mcp_shared/permissioned_tool.py`.

## Prerequisites

- Shared package is installed or editable-linked (`packages/unifi-mcp-shared`)
- The tool module will be imported in `main.py` so the decorator chain is wired before the server starts
- For new tool authors: read at least one existing mutating tool for reference (e.g., `apps/network/src/unifi_network_mcp/tools/devices.py`, `apps/network/src/unifi_network_mcp/tools/client_groups.py`)
- Understanding of the two-axis model before modifying any mutating tools or permission-related code

## Procedure A: Server-Level Setup with setup_permissioned_tool()

`setup_permissioned_tool()` is called **once at server init** — it replaces `server.tool` with the permissioned decorator. It is **not** called per-tool. All app context (category_map, server_prefix, logger, etc.) flows in as DI parameters. Never import app-level config inside `unifi-mcp-shared` or `unifi-core`.

```python
from unifi_mcp_shared.permissioned_tool import setup_permissioned_tool

# Called once at server init — replaces server.tool with the permissioned decorator
setup_permissioned_tool(
    server=server,
    category_map=category_map,           # e.g., {\"network\": \"network\", \"devices\": \"device\"}
    server_prefix=server_prefix,         # e.g., \"NETWORK\" — used for env var resolution
    register_tool_fn=register_tool,      # callback to add tool to tool_index
    diagnostics_enabled_fn=lambda: diag, # callable returning bool
    wrap_tool_fn=wrap_with_diagnostics,  # diagnostics wrapper
    logger=logger,
)
# After this call, @server.tool() IS the permissioned decorator
```

If you see `from app.settings import permission_mode` inside `unifi-mcp-shared` or `unifi-core`, that is a DI regression — report it and revert.

## Procedure B: Understanding the Two-Axis Permission Model

The permission system has exactly two independent axes. Conflating them causes architectural errors and incorrect PR review feedback.

**Axis 1 — Permission mode (caller-controlled, runtime)**

The caller passes `permission_mode` at invocation time:

- `confirm` (default): the tool enters preview mode on first call; the caller must re-invoke with `confirm=True` to execute the mutation.
- `bypass`: skip the preview step and execute immediately. Only permitted when the admin has granted bypass for this tool category in the server config.

This axis is dynamic — the same tool behaves differently depending on what the caller passes. It is NOT a configuration-time setting.

**Axis 2 — Policy gates (admin-controlled, config-time)**

Each tool category has a policy gate that is either enabled or disabled by the administrator in the server configuration. A disabled gate blocks execution for all callers regardless of `permission_mode`.

Key invariant: **tools are always registered and visible regardless of policy gates.** The gate blocks at *execution time*, not at *registration time*. Never assume a tool appearing in the MCP tool list is unrestricted — it may be gated off. Agents must not treat tool visibility as a proxy for permission.

## Procedure C: Declare Permissions on a New Mutating Tool

After server setup, declare `permission_category` and `permission_action` as **decorator kwargs** passed to `@server.tool()`. Both are required. Missing either causes the tool to bypass the safety layer silently (the decorator's fast path fires).

```python
@server.tool(
    name=\"unifi_update_my_resource\",
    description=\"Update a resource\",
    permission_category=\"your_category\",  # e.g. \"network\", \"firewall\", \"devices\", \"dns\"
    permission_action=\"update\",           # \"update\", \"create\", or \"delete\"
    annotations=ToolAnnotations(readOnlyHint=False, ...),
)
async def update_my_resource(
    resource_id: str,
    confirm: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    ...
```

At runtime, `server.tool` is the permissioned decorator installed by `setup_permissioned_tool()` in `main.py`. It intercepts `permission_category` and `permission_action` from the decorator's own kwargs — they are NOT forwarded to the function body and must NOT appear in the function signature.

`confirm: bool = False` is the only permission-related function parameter. It controls which branch (preview vs. execute) the function takes. The decorator injects `confirm=True` automatically in bypass mode by inspecting the signature — a missing parameter silently breaks bypass mode.

Choose the correct `category`: Category strings map to admin-configured policy gates. Use the same string as other tools in the same domain (all DNS tools share one category, all device tools share another). Check existing tools in the same module for the canonical string — e.g., `\"devices\"` in `tools/devices.py`, `\"client_group\"` in `tools/client_groups.py`.

## Procedure D: Choosing and Using Confirmation Helpers

All helpers are in `packages/unifi-core/src/unifi_core/confirmation.py` and re-exported from `unifi_mcp_shared`:

| Helper | Use for | Key `preview` shape |
|---|---|---|
| `update_preview(resource_type, resource_id, resource_name, current_state, updates)` | Update operations | `{\"current\": {changed fields only}, \"proposed\": {delta}}` |
| `toggle_preview(resource_type, resource_id, resource_name, current_enabled)` | Enable/disable | `{\"current\": {\"enabled\": bool}, \"proposed\": {\"enabled\": !bool}}` |
| `create_preview(resource_type, resource_data, resource_name)` | Create operations | `{\"will_create\": {full payload}}` |
| `preview_response(action, resource_type, resource_id, current_state, proposed_changes)` | Custom / base | `{\"current\": {...}, \"proposed\": {...}}` |

All helpers return a response with the same envelope:

```json
{
  \"success\": true,
  \"requires_confirmation\": true,
  \"action\": \"update\",
  \"resource_type\": \"network\",
  \"resource_id\": \"abc123\",
  \"preview\": { \"current\": {...}, \"proposed\": {...} },
  \"message\": \"Will update name on network 'abc123'. Set confirm=true to execute.\"
}
```

**Critical:** The key inside `preview` is `\"proposed\"` (not `\"proposed_changes\"`). Consumer code reading `response[\"preview\"][\"proposed_changes\"]` returns `None` silently. This is the most common integration mistake with these helpers.

**`update_preview` filters `current_state`:** It automatically narrows `current_state` to only the keys being updated. This is intentional — reviewers see the before/after only for fields being changed, not the full resource.

**Why `success: true` in previews:** A preview is itself a successful operation. `success: true` means \"the preview was built without error.\" It does NOT mean the mutation ran. Always check `requires_confirmation` to distinguish.

## Procedure E: Consumer-Side Preview Reading

Any MCP client or agent calling a mutating tool must handle the two-stage response:

```python
response = await call_tool(\"update_network_config\", {
    \"network_id\": \"abc123\",
    \"name\": \"new-name\",
})

if response.get(\"requires_confirmation\"):
    # First call returned a preview — nothing was changed.
    print(\"Current:\", response[\"preview\"][\"current\"])
    print(\"Proposed:\", response[\"preview\"][\"proposed\"])  # key is \"proposed\", not \"proposed_changes\"

    # User approves → re-invoke with confirm=True AND all original fields
    result = await call_tool(\"update_network_config\", {
        \"network_id\": \"abc123\",
        \"name\": \"new-name\",   # must re-send delta fields
        \"confirm\": True,
    })
else:
    # Bypass mode or already confirmed.
    result = response
```

**Gotcha — silent preview trap:** Skipping the `requires_confirmation` check and treating a preview as completed (because `success` is `true`) means the change is never applied. The caller silently believes the operation succeeded. This is the most common consumer-side integration bug.

**Bypass mode:** When `UNIFI_TOOL_PERMISSION_MODE=bypass` (or `UNIFI_<SERVER>_TOOL_PERMISSION_MODE=bypass`), the decorator injects `confirm=True` before calling the function. The consumer pattern above handles both modes correctly without branching on mode.

**Incomplete second call:** The second call must include all original delta fields plus `confirm=True`. Sending only `{\"confirm\": True, \"network_id\": \"abc123\"}` produces empty kwargs — no change is applied and no error is raised.

## Procedure F: Preview Semantics — Delta, Not Merged Result

The `preview.proposed` block returned in the preview step shows **the caller's partial update intent (the delta)**, not the deep-merged final object that will be written to the device.

Example: caller sends `{\"vlan_id\": 10}` as the update payload → `preview.proposed` shows `{\"vlan_id\": 10}`, and `preview.current` shows the current value of `vlan_id` only. The full config is not shown.

The executor applies `deep_merge(current_state, delta)` (from `unifi_core.merge.deep_merge`) at confirm time against a freshly fetched current state (see Procedure G). The preview is a fidelity check on what the caller intends to change, not a simulation of the final API payload.

**PR review implication:** Do not flag a preview as incomplete because it doesn't show the full merged config. A reviewer asking \"why doesn't the preview show the final merged object?\" is applying the wrong model. The delta-preview design is correct and intentional.

If you need to inspect the merged result in a debug or test context, call `deep_merge(current_state, delta)` yourself — import from `unifi_core.merge`. The preview pathway does not expose this.

## Procedure G: Preserve the Double-Fetch at Confirm Time

When `confirm=True`, the tool **re-fetches the current state from the API** before merging and writing. This appears redundant if you only see the code path. It is not.

**Why it must stay — TOCTOU prevention:**

The preview call (step 1) fetched state₁ to generate the delta preview. By the time the confirm call (step 2) arrives, the device may have changed (another admin, another tool, a background sync). Reusing the step-1 fetch would merge the delta against a stale base:

```
Step 1: fetch state₁ → show delta preview
   ... time passes, another change lands ...
Step 2 (confirm): re-fetch state₂ → deep_merge(state₂, delta) → write ✓
```

Without the re-fetch, step 2 would use state₁ as the merge base — classic time-of-check/time-of-use race, silently overwriting the intervening change.

**Do not optimize this away.** If a reviewer or profiler flags the double-fetch as a redundant API call, explain the TOCTOU rationale. It is a correctness requirement, not an oversight.

## Procedure H: Test Isolation via Decorator Replacement

The full permission enforcement chain is only wired in the live server via `main.py`. The `runtime.py` module installs a lightweight wrapper (`_create_permissioned_tool_wrapper`) that strips `permission_category`, `permission_action`, and `auth` kwargs before passing through to FastMCP — it does not enforce policy gates or run the preview/confirm state machine.

**What this means in practice:**

- Unit tests that import the tool function directly (not via the MCP server) bypass the policy gate and the two-step state machine. This is intentional — it lets tests exercise tool logic in isolation without needing a full server context.
- The `runtime.py` wrapper pops `permission_category`/`permission_action` from the **decorator's** kwargs before they reach FastMCP. The function signature never has these params — this is expected behavior, not a bug.
- To test the full permission/confirmation flow end-to-end, use integration tests that invoke through the live MCP server stack (not direct function import).

**Do not put permission logic inside the function body.** Permission routing belongs in the decorator layer (`permissioned_tool.py`), not in individual tool functions. Any branching on `permission_category` inside a tool function will never see those values — they are consumed by the decorator layer before the function body runs.

## Procedure I: Permission Mode vs. Policy Gates — Orthogonal Axes

These two safety mechanisms are independent and must not be conflated.

| Axis | Controls | Configured via | Trigger behavior |
|---|---|---|---|
| **Permission mode** | Workflow (preview vs. immediate execute) | `UNIFI_TOOL_PERMISSION_MODE` / `UNIFI_<SERVER>_TOOL_PERMISSION_MODE` env var | `\"confirm\"` → two-stage; `\"bypass\"` → inject `confirm=True` |
| **Policy gates** | Hard on/off per tool | `PolicyGateChecker` / `category_map` config | Blocked tools return `{\"success\": False, \"error\": \"...\"}` on **any** call |

**Key rules:**

1. **Tools are always visible** — policy gates never hide a tool from the tool list. They block at call time. Callers see the tool, invoke it, and receive a denial error. Tool hiding would break capability negotiation.

2. **Gates fire on every call** — the policy gate check runs at the top of the `gated_func` wrapper, before any `confirm` branching. A gated tool returns an error on the first call (preview) AND the second call (confirm). There is no \"preview-passes, gate-on-confirm\" behavior.

3. **Mode and gates are independent** — `permission_mode=bypass` does not override a policy gate. A gated tool in bypass mode is still gated. \"Bypassing the two-stage flow\" ≠ \"bypassing policy restrictions.\"

**Debugging guide:**

```
Tool returns error on first OR second call?
  → Check PolicyGateChecker config for the tool's category + action.
  → category_map and policy_gates come from the app layer, not unifi-core.

Tool executes immediately without preview?
  → Check UNIFI_TOOL_PERMISSION_MODE or UNIFI_<SERVER>_TOOL_PERMISSION_MODE.
  → \"bypass\" causes decorator to inject confirm=True before calling the function.

Tool blocked even in bypass mode?
  → Policy gate is active — check policy_gates config, not permission_mode.
```

## Cross-Cutting Gotchas

**1. `success: true` is ambiguous — always check `requires_confirmation` first.** Preview responses set `success: true` to signal successful preview generation, not a completed mutation. Any agent code that reads only `success` will silently skip the confirmation prompt and falsely believe the mutation succeeded.

**2. `\"proposed\"` vs `\"proposed_changes\"`** — the key inside `preview` is `\"proposed\"` in all helpers. Consumer code reading `response[\"preview\"][\"proposed_changes\"]` returns `None` silently.

**3. Tool visibility ≠ permission.** A tool appearing in the MCP tool list does not mean it is unrestricted. Policy gates block at execution time. Never infer from tool visibility that a call will succeed.

**4. The preview shows the delta, not the merged result.** The correct question when reviewing a preview is \"does this show what the caller intends to change?\" not \"does this match what the API will receive?\"

**5. Double-fetch is TOCTOU prevention, not waste.** Eliminating the re-fetch at confirm time introduces a silent correctness bug whenever state changes between the preview and confirm calls.

**6. `permission_category`/`permission_action` belong in the decorator call, not the function signature.** Adding them to the function signature is wrong — they're consumed at decoration time, before the function body is ever called.

**7. Missing `confirm` parameter** — every mutating tool must declare `confirm: bool = False`. Bypass injection inspects the function signature; if the param is missing, bypass mode silently fails to inject `confirm=True`.

**8. DI violation in shared packages** — `unifi-mcp-shared` and `unifi-core` must never import application-level config. All context flows in via `setup_permissioned_tool()`. If you see `from app.settings import ...` inside these packages, that is a regression.

**9. Incomplete second call** — must include all original delta fields plus `confirm=True`. Empty kwargs → empty merge → no change, no error.
