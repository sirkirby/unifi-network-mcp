---
name: myco:validator-registry-governance
description: |
  Covers the full validator registry and schema governance lifecycle for
  this project: registering a new schema in UniFiValidatorRegistry,
  choosing validate() vs validate_and_apply_defaults() for update vs
  create paths, enforcing validated_data discipline so raw input never
  reaches the API, adding additionalProperties: false to UPDATE schemas
  (layer-2 hardening), auditing the registry for coverage gaps, and
  respecting the ResourceValidator blast-radius safety constraint. Apply
  this skill whenever adding a new tool category, reviewing a community
  PR, hardening existing schemas, or debugging a validator-related merge
  blocker — even if the user doesn't explicitly ask about the validator
  registry.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Validator Registry and Schema Governance

The validator registry is the project's contract between tool implementations and the UniFi API. Every tool that accepts user input must be registered in its app server's validator registry and must call one of the two canonical validation methods. Misconfiguration has caused merge blockers in PRs #123, #126, and #146 — the procedures here encode those lessons so future contributors don't repeat them.

## Prerequisites

- Know which app server owns the tool: `network`, `protect`, or `access`
- Locate the app server's `validator_registry.py` (e.g., `apps/network/src/unifi_network_mcp/validator_registry.py`)
- Know the schema name and its operation type: CREATE or UPDATE

## Procedure A: Register a New Schema

1. **Locate the registry file** for the owning app server:
   ```
   apps/<app>/src/unifi_<app>_mcp/validator_registry.py
   ```
   Each app has its own isolated registry class (`UniFiValidatorRegistry` for network, `ProtectValidatorRegistry` for protect, and so on). Do not cross-register — a network schema in the protect registry will never be found.

2. **Import the schema** at the top of the registry file alongside existing imports:
   ```python
   from .schemas import (
       EXISTING_SCHEMA,
       YOUR_NEW_SCHEMA,
   )
   ```

3. **Add an entry to the `_validators` class dict.** There is no `register()` method — the registry is a class-level dict of `ResourceValidator` instances. Add your entry in the `_validators` block:
   ```python
   _validators = {
       # ... existing entries ...
       "your_tool_name": ResourceValidator(YOUR_NEW_SCHEMA, "Human Label"),
       "your_tool_name_update": ResourceValidator(YOUR_UPDATE_SCHEMA, "Human Label Update"),
   }
   ```
   Use the tool's function name (snake_case, no `unifi_` prefix) as the dict key. Mismatches between the key and the tool function name produce silent validation bypasses — the registry returns `(False, "No validator found for...", None)` at runtime.

4. **Verify manually.** There is no project-wide CI gate that enforces full tool-to-validator coverage. Verify by grepping both the tool module and the registry file and comparing names (see Procedure E).

**Gotcha — import before dict entry:** The schema constant must be imported before the `_validators` dict references it. A missing import produces a `NameError` at module load time, not at call time.

## Procedure B: Choose validate() vs validate_and_apply_defaults()

This method-selection decision is the most repeated merge blocker in the project. Both methods are class methods on the registry, called the same way, but with different semantics:

| Method | Injects schema defaults? | Use for |
|---|---|---|
| `UniFiValidatorRegistry.validate("key", data)` | **No** | UPDATE tools — partial input; omitted fields mean "leave unchanged" |
| `UniFiValidatorRegistry.validate_and_apply_defaults("key", data)` | **Yes** | CREATE tools — full resource; omitted fields get schema defaults |

**Both methods return a 3-tuple:** `(is_valid: bool, error_msg: str | None, validated_data: dict | None)`. Always unpack all three:
```python
is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("wlan_update", update_data)
```

**Decision rule:**
- Tool sends PATCH or PUT to modify an existing resource → use `validate()`
- Tool POSTs to create a new resource → use `validate_and_apply_defaults()`

**Why this matters:** Using `validate_and_apply_defaults()` on an update path silently overwrites existing resource fields with schema defaults. Example from PR #146: calling `update_firewall_policy({"name": "new name"})` with the wrong method would also inject `create_allow_respond: False`, `match_ip_sec: False`, `ip_version: "BOTH"`, `schedule: {"mode": "ALWAYS"}` — silent data loss tracked in issue #113.

**Real PR examples:**
- **PR #123** (WLAN/radio tools): `validate_and_apply_defaults()` on the radio update path injected defaults into partial updates
- **PR #146** (zone-based firewall): `validate_and_apply_defaults()` on the update path was the root merge blocker; maintainer had to take over implementation
- **PR #126** (SNMP backup tools): `validate()` was called correctly but the return value was mishandled — see Procedure C

## Procedure C: Enforce validated_data Discipline

Both `validate()` and `validate_and_apply_defaults()` return a 3-tuple. Unpack it and use `validated_data` — the raw input dict must never be forwarded to the API after a validation call.

**Correct pattern:**
```python
is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("resource_update", payload)
if not is_valid:
    return {"success": False, "error": error_msg}
result = await manager.update_resource(resource_id, validated_data)
```

**Wrong pattern (PR #126 bug):**
```python
is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("resource_update", payload)
# no is_valid check, and raw payload forwarded instead of validated_data:
result = await manager.update_resource(resource_id, payload)  # ← still the raw dict
```

**Review checklist for any tool implementation:**
1. Is `UniFiValidatorRegistry.validate()` or `validate_and_apply_defaults()` called?
2. Is the 3-tuple unpacked into all three variables?
3. Is `if not is_valid:` checked before proceeding?
4. Is `validated_data` (not the original input) what gets passed to the manager or HTTP call?

**Gotcha — validate() does NOT raise on invalid input.** Both methods catch all exceptions internally and return `(False, error_msg, None)`. Code that wraps the call in a bare `try/except` expecting a raise will silently swallow the error. Always check `if not is_valid:` after the call.

## Procedure D: Add additionalProperties: false to UPDATE Schemas

Layer-2 JSON Schema hardening prevents unknown or misspelled fields from silently passing through on update paths. This is an active open work item — every `*_UPDATE_SCHEMA` in the project's `schemas.py` files should have it.

**How to add it** (file: `apps/<app>/src/unifi_<app>_mcp/schemas.py`):
```python
YOUR_RESOURCE_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "enabled": {"type": "boolean"},
        # ... declared fields ...
    },
    "additionalProperties": False,   # ← add this line
}
```

**Why UPDATE schemas specifically?** CREATE schemas sometimes permit extra fields for forward-compatibility. UPDATE schemas are the enforcement boundary — they define exactly what a caller is allowed to change, so unknown fields should be rejected, not silently forwarded to the API.

**Finding schemas that still need it:**
```bash
grep -n "_UPDATE_SCHEMA" apps/*/src/*/schemas.py \
  | grep -v "additionalProperties"
```
Any hit here is a candidate for hardening.

## Procedure E: Audit the Registry for Coverage Gaps

Manual audits are necessary when adding tools to an existing module or reviewing a community PR. There is no automated project-wide coverage gate.

1. **List all tool functions** in a module:
   ```bash
   grep -n "^async def\|^def " apps/<app>/src/unifi_<app>_mcp/<module>.py
   ```

2. **List registered names** in the app's registry:
   ```bash
   grep -n "\"[a-z_]*\":" apps/<app>/src/unifi_<app>_mcp/validator_registry.py
   ```

3. **Compare** — every public tool function should have a corresponding key in the `_validators` dict. Helpers and private functions (`_prefixed`) don't need registration.

**Current known gap:** `devices.py` in the network app has 3 tools with no registered validators (as of the last audit). These are tracked and should be resolved when the device tools are next extended.

**When to audit:**
- Before opening a PR that adds tools to an existing module
- During community PR review (validator registry is a mandatory review gate)
- When a tool silently bypasses validation (symptom: unvalidated API calls succeed with unexpected fields)

## Procedure F: ResourceValidator Blast-Radius Safety

**The constraint:** Schema default injection must never be added to the shared `ResourceValidator.validate()` method in `packages/unifi-core/src/unifi_core/validators.py`.

**Why the blast radius is large:** `ResourceValidator` is the base class used by every registry entry across all app servers. There are 37+ properties with `"default":` in the network app's `schemas.py` alone. If defaults were injected in `validate()`, every partial-update call project-wide would silently overwrite existing fields — data loss at scale across network, protect, and access tools simultaneously.

**Where defaults belong instead:**
- In `validate_and_apply_defaults()` — an explicit opt-in method called only on create paths (already implemented correctly in `ResourceValidator`)
- In the create tool's own code, applied before or after validation
- **Not** in `ResourceValidator.validate()` or any shared base class method

**Diagnosis when a PR touches the shared validator:**
1. Does the PR add default injection to `validate()`? → immediate concern, must redirect
2. Measure downstream callers to understand blast radius:
   ```bash
   grep -rn "\.validate(" apps/ | grep -v "test_"
   ```
3. Redirect the contributor to apply defaults in the specific create tool or via `validate_and_apply_defaults()`

**PR #146 case study:** A community contributor modified the shared validator to inject `schedule: {"mode": "ALWAYS"}` and `create_allow_respond: False` for zone-based firewall creation. These are real API requirements (firmware 5.x rejects policies without them), but the fix location was wrong. The correct implementation applies those defaults inside `create_firewall_policy()` directly — or via an explicit `validate_and_apply_defaults()` call — keeping the shared base clean.

## Cross-Cutting Gotchas

- **Each app has its own registry class.** `UniFiValidatorRegistry` (network), `ProtectValidatorRegistry` (protect). Registering in the wrong app's `validator_registry.py` means the tool's app server never finds the validator.
- **Key must match tool function name exactly.** `"update_wlan"` in `_validators` only matches a tool function named `update_wlan`. Typos cause silent validation bypass.
- **Both methods return a 3-tuple; neither raises.** Always unpack `is_valid, error_msg, validated_data =` and check `if not is_valid:`. The `validated_data` is `None` on failure.
- **`validated_data` is the post-validation dict; the original input is pre-validation.** Always forward `validated_data` to managers and HTTP calls.
- **Community PR mandatory gates:** validator key present in `_validators`, correct method for the operation type (update vs create), 3-tuple fully unpacked, and `validated_data` used downstream. Flag all four before approving.
