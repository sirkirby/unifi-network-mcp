---
name: myco:schema-validator-management
description: |
  Apply this skill whenever writing, extending, or reviewing schema definitions
  or validator hookups in unifi-mcp — even if the user doesn't explicitly ask
  about validation. Covers the full schema layer workflow: (1) writing *_SCHEMA
  and *_UPDATE_SCHEMA entries in schemas.py with proper types, bounds, and
  inheritance via copy.deepcopy; (2) registering schemas in UniFiValidatorRegistry
  in validator_registry.py; (3) hooking validators into tools with the validated_data
  contract; (4) choosing validate() vs validate_and_apply_defaults() for update
  vs create paths; (5) layer-2 hardening with additionalProperties: false on all
  *_UPDATE_SCHEMA entries; (6) the ResourceValidator blast-radius rule — default
  injection must never live in the shared base validate() method; (7) auditing the
  registry for coverage gaps; and (8) comprehensive validation unit tests covering
  both create and update paths.
managed_by: myco
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob
---

# Schema Definition and Validator Management

This skill covers the complete schema validation layer in unifi-mcp — from writing
JSON Schema entries for tool parameters through registering them with the validator
registry, choosing the right validation method, and consuming validated output safely
in tool implementations. Errors in this layer cause silent data loss or live-controller
corruption, so each step carries a hard rule.

**Canonical reference implementation:** \`update_wlan\` at line 682 in
\`apps/network/src/unifi_network_mcp/tools/network.py\`.

## Prerequisites

- The tool's API parameters are known (exact field names as expected by the UniFi
  controller, not inferred — see §1 on prefix correctness)
- You know whether this is a **create** tool or an **update** tool; the distinction
  determines whether defaults belong in the schema (they don't for update tools)
- You have access to \`schemas.py\` and \`validator_registry.py\` in the relevant app
  package (\`apps/network/src/unifi_network_mcp/\` for the network app)
- Each app server has its own isolated registry class (e.g., \`UniFiValidatorRegistry\`
  for network, \`ProtectValidatorRegistry\` for protect)

## Procedure 1: Write the Schema Entry in schemas.py

Schema definitions live in \`apps/network/src/unifi_network_mcp/schemas.py\`.

### Naming conventions

| Purpose | Constant name | Registry key |
|---|---|---|
| Create tool | \`RESOURCE_SCHEMA\` | \`"resource_create"\` |
| Update tool | \`RESOURCE_UPDATE_SCHEMA\` | \`"resource_update"\` |

Examples: \`WLAN_SCHEMA\` / \`"wlan_create"\`, \`DEVICE_RADIO_UPDATE_SCHEMA\` /
\`"device_radio_update"\`, \`SNMP_SETTINGS_UPDATE_SCHEMA\` / \`"snmp_settings_update"\`.

### Schema structure

\`\`\`python
DEVICE_RADIO_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "antenna_gain":          {"type": "integer", "minimum": 0,   "maximum": 30},
        "tx_power":              {"type": "integer", "minimum": 0,   "maximum": 100},
        "tx_power_mode":         {"type": "string",  "enum": ["auto", "low", "medium", "high", "custom"]},
        "min_rssi":              {"type": "integer", "minimum": -95, "maximum": -20},
        "min_rssi_enabled":      {"type": "boolean"},
        "sens_level":            {"type": "integer", "minimum": -95, "maximum": -20},
        "sens_level_enabled":    {"type": "boolean"},
        "vwire_enabled":         {"type": "boolean"},
        "assisted_roaming_enabled": {"type": "boolean"},
    },
    "additionalProperties": False,  # Required on all *_UPDATE_SCHEMA — see Procedure 5
}
\`\`\`

**Always add \`minimum\`/\`maximum\` for numeric fields when bounds are known.** Omitting
them lets invalid values silently pass through. In PR #123, \`sens_level\` initially had
no bounds; they were added during review to mirror \`min_rssi\` (−95/−20).

### Schema inheritance

When an update schema shares most properties with a create schema, use
\`copy.deepcopy\` rather than re-declaring fields:

\`\`\`python
import copy

NETWORK_UPDATE_SCHEMA = copy.deepcopy(NETWORK_SCHEMA)
NETWORK_UPDATE_SCHEMA["additionalProperties"] = False
# Add or remove individual properties as needed
NETWORK_UPDATE_SCHEMA["properties"].pop("some_create_only_field", None)
\`\`\`

### Do NOT add \`"default":\` values to \`*_UPDATE_SCHEMA\` entries

Defaults belong only in create-specific schemas or create-specific code paths.
Adding them to update schemas enables accidental default injection — see Procedure 6
for the full blast-radius explanation.

### Field prefix correctness — silent failure on live controller

Use the **exact** field name prefix the UniFi controller expects. A single wrong
prefix causes the API to silently ignore the field — the call returns success, but
the setting is never applied.

**PR #131 example:** \`dhcp_*\` vs \`dhcpd_*\` — the controller expects \`dhcpd_enabled\`,
\`dhcpd_start\`, \`dhcpd_stop\`. Using \`dhcp_*\` was a latent bug in \`create_network\`
that only surfaced during schema review; it would have silently failed on any real
network with DHCP.

**Verification method:** Check raw API responses for the resource type, or grep
existing working schemas for the resource to confirm the expected prefix:

\`\`\`bash
grep -n "dhcpd_" apps/network/src/unifi_network_mcp/schemas.py
\`\`\`

## Procedure 2: Register the Schema in validator_registry.py

Writing a schema constant does **not** register it. These are always two separate
changes in two separate files. A PR that adds only the schema definition is
incomplete — the tool will raise \`KeyError\` at runtime when the unregistered key
is passed to \`validate()\`.

Registry file: \`apps/network/src/unifi_network_mcp/validator_registry.py\`

Each app server has its own isolated registry class (\`UniFiValidatorRegistry\` for network,
\`ProtectValidatorRegistry\` for protect, etc.). Do not cross-register — a network schema
in the protect registry will never be found.

\`\`\`python
from .schemas import (
    # ... existing imports ...
    DEVICE_RADIO_UPDATE_SCHEMA,   # ← add
)
from .validators import ResourceValidator

class UniFiValidatorRegistry:
    _validators = {
        # ... existing entries ...
        "device_radio_update": ResourceValidator(DEVICE_RADIO_UPDATE_SCHEMA, "Device Radio Update"),  # ← add
    }
\`\`\`

**Three things must all be present for registration to be complete:**

1. \`schemas.py\` — schema constant defined ✓
2. \`validator_registry.py\` — schema constant imported at top ✓
3. \`validator_registry.py\` — key added to \`_validators\` dict as \`ResourceValidator(SCHEMA, "Label")\` ✓

**Gap detection:** PR #123 found \`DEVICE_RADIO_UPDATE_SCHEMA\` existed but was
unregistered. PR #119 found \`create_ap_group\` and \`update_ap_group\` had no schemas
at all. When reviewing PRs that add or touch schemas, verify explicitly:

\`\`\`bash
grep -n "device_radio_update\\|DEVICE_RADIO_UPDATE" \\
  apps/network/src/unifi_network_mcp/validator_registry.py
\`\`\`

**Key matching gotcha:** The dict key in \`_validators\` must match the tool function name
exactly. \`"update_wlan"\` in \`_validators\` only matches a tool named \`update_wlan\`.
Typos cause silent validation bypass — the registry returns \`(False, "No validator found...", None)\`.

## Procedure 3: Hook the Validator into the Tool & Enforce validated_data Discipline

Once the schema is registered, wire the validator into the tool function before the
API call.

### Import

\`\`\`python
from unifi_network_mcp.validator_registry import UniFiValidatorRegistry
\`\`\`

### The validate pattern

Both validate methods are **class methods** that return a 3-tuple:
\`(is_valid: bool, error_msg: str | None, validated_data: dict | None)\`.

**Always unpack all three values:**

\`\`\`python
is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate(
    "device_radio_update", updates
)
if not is_valid:
    return {"success": False, "error": f"Invalid radio update data: {error_msg}"}

# Pass validated_data to the API — NEVER the original input dict
response = await device_manager.update_device_radio(mac_address, validated_data)
\`\`\`

**\`validated_data\` is a post-validation dict; use it, not the original.** Calling
\`validate()\` and then ignoring the third element — passing the original dict
downstream instead — silently discards type coercions and schema-applied
transformations. The API call succeeds but may receive wrong data.

This mistake has recurred across three PRs from three different contributors:

| PR | Tool | Mistake | Fix |
|---|---|---|---|
| #123 | \`update_device_radio\` | Return value discarded, original \`updates\` passed | \`66fe214\` |
| #126 | \`update_snmp_settings\` | \`payload\` used instead of \`validated_data\` | \`89a9998\` |
| #146 | firewall policy tool | Same pattern | merge-blocked |

**Code review gate:** For every \`UniFiValidatorRegistry.validate(\` in a PR, confirm:
1. All three return values are unpacked: \`is_valid, error_msg, validated_data = ...\`
2. \`is_valid\` is checked before proceeding
3. \`validated_data\` — not the original variable — reaches the API call

### Cross-field validation stays as inline code

JSON Schema cannot express cross-field dependencies (e.g., \`tx_power\` is only
meaningful when \`tx_power_mode == "custom"\`; \`sens_level\` pairs with
\`sens_level_enabled\`). Keep cross-field paired validation as explicit \`if\` guards
in the tool function. Do not attempt to encode these in the schema.

## Procedure 4: Choose validate() vs validate_and_apply_defaults()

Both methods are on the registry class. The distinction is **critical** for update vs create paths:

| Method | Injects schema defaults? | Use for |
|---|---|---|
| \`UniFiValidatorRegistry.validate("key", data)\` | **No** | UPDATE tools — partial input; omitted fields mean "leave unchanged" |
| \`UniFiValidatorRegistry.validate_and_apply_defaults("key", data)\` | **Yes** | CREATE tools — full resource; omitted fields get schema defaults |

**Decision rule:**
- Tool sends PATCH or PUT to modify an existing resource → use \`validate()\`
- Tool POSTs to create a new resource → use \`validate_and_apply_defaults()\`

**Why this matters:** Using \`validate_and_apply_defaults()\` on an update path silently
overwrites existing resource fields with schema defaults. Example from PR #146:
calling \`update_firewall_policy({"name": "new name"})\` with the wrong method would
also inject \`create_allow_respond: False\`, \`match_ip_sec: False\`, \`ip_version: "BOTH"\`,
\`schedule: {"mode": "ALWAYS"}\` — silent data loss tracked in issue #113.

**Real PR examples:**
- **PR #123** (WLAN/radio tools): \`validate_and_apply_defaults()\` on the radio update path
- **PR #146** (zone-based firewall): \`validate_and_apply_defaults()\` on the update path was the root merge blocker
- **PR #126** (SNMP backup tools): \`validate()\` was called correctly but the return value was mishandled

**Gotcha — validate() does NOT raise on invalid input.** Both methods catch all exceptions
internally and return \`(False, error_msg, None)\`. Code that wraps the call in a bare
\`try/except\` expecting a raise will silently swallow the error. Always check \`if not is_valid:\`
after the call.

## Procedure 5: Layer-2 Hardening — additionalProperties: false

All \`*_UPDATE_SCHEMA\` entries must include \`"additionalProperties": False\`. This
rejects unknown keys at validation time rather than silently forwarding them to
the API.

\`\`\`python
WLAN_UPDATE_SCHEMA = {
    "type": "object",
    "properties": { ... },
    "additionalProperties": False,  # Blocks typos and undeclared fields
}
\`\`\`

**Why update tools specifically:** Update tools build a partial payload from only
the caller-provided fields. Without this gate, a field name typo (e.g., \`"tx_powr"\`)
passes validation, is forwarded to the API, and is silently ignored — the user sees
success but the setting never changed.

**Open work item:** Not all existing \`*_UPDATE_SCHEMA\` entries in
\`apps/network/src/unifi_network_mcp/schemas.py\` have \`additionalProperties: False\`.
When touching any existing update schema, add this field if it is missing — it is a
non-breaking addition for correctly-written callers.

## Procedure 6: ResourceValidator Blast-Radius Rule

**Never inject defaults inside \`ResourceValidator.validate()\` in
\`packages/unifi-core/src/unifi_core/validators.py\`.**

### Why this is a hard architectural constraint

The shared \`validate()\` method is called by every tool across network, protect, and
access app packages. Adding default injection there means every \`.validate()\` call
project-wide silently injects defaults for any missing top-level field that has a
\`"default":\` in its schema.

The blast radius is severe for **update tools**, which intentionally omit fields to
mean "leave this unchanged." With default injection, those omitted fields would be
overwritten with schema defaults — silent data loss on production resources.

**Concrete PR #146 example:**

\`\`\`python
# Caller intent: update only the policy name
update_firewall_policy({"name": "new name"})

# With default injection in validate(), validated_data silently becomes:
{
    "name": "new name",
    "create_allow_respond": False,   # ← overwrites existing live setting
    "match_ip_sec": False,           # ← overwrites existing live setting
    "ip_version": "BOTH",            # ← overwrites existing live setting
    "schedule": {"mode": "ALWAYS"},  # ← overwrites existing live setting
}
\`\`\`

There are 37+ properties with \`"default":\` values in \`schemas.py\` (network app
alone). Default injection in the shared validator would trigger for all of them
on every \`.validate()\` call (tracked in issue #113).

### Where defaults belong — validate_and_apply_defaults()

For **create tools** that genuinely need schema defaults applied, use the opt-in
method \`UniFiValidatorRegistry.validate_and_apply_defaults()\` instead of the
base \`validate()\`:

\`\`\`python
# Create path only — opt-in default injection
is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate_and_apply_defaults(
    "firewall_policy_create", policy_data
)
\`\`\`

This method applies \`"default":\` values from the schema for missing top-level keys,
but only when explicitly called. The base \`validate()\` never injects defaults.

**Defaults must NEVER live in \`*_UPDATE_SCHEMA\` entries regardless.** Separate the
schemas: create schemas may have defaults; update schemas must not.

**Review gate:** Any PR modifying \`packages/unifi-core/src/unifi_core/validators.py\`
to add default injection to the base \`validate()\` method is a merge blocker. Post a
request-changes review citing the blast radius and issue #113.

## Procedure 7: Audit the Registry for Coverage Gaps

Manual audits are necessary when adding tools to an existing module or reviewing a
community PR. There is no automated project-wide coverage gate.

1. **List all tool functions** in a module:
   \`\`\`bash
   grep -n "^async def\\|^def " apps/<app>/src/unifi_<app>_mcp/<module>.py
   \`\`\`

2. **List registered names** in the app's registry:
   \`\`\`bash
   grep -n '\\"[a-z_]*\\"' apps/<app>/src/unifi_<app>_mcp/validator_registry.py
   \`\`\`

3. **Compare** — every public tool function should have a corresponding key in the
   \`_validators\` dict. Helpers and private functions (\`_prefixed\`) don't need registration.

**Current known gap:** \`devices.py\` in the network app has 3 tools with no registered
validators (as of the last audit). These are tracked and should be resolved when the
device tools are next extended.

**When to audit:**
- Before opening a PR that adds tools to an existing module
- During community PR review (validator registry is a mandatory review gate)
- When a tool silently bypasses validation (symptom: unvalidated API calls succeed with unexpected fields)

## Cross-Cutting Gotchas

### The \`payload\` variable trap (most common community error)

The pattern \`is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate("key", payload)\`
is correct — but contributors then write \`api.put(url, payload)\` from muscle memory:

\`\`\`python
# ❌ Wrong — silently discards coercions, uses original dict
is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate(
    "snmp_settings_update", payload
)
await self._api.put(url, payload)            # BUG: original dict

# ✅ Correct
is_valid, error_msg, validated_data = UniFiValidatorRegistry.validate(
    "snmp_settings_update", payload
)
await self._api.put(url, validated_data)     # validated output
\`\`\`

When reviewing PRs, scan every \`UniFiValidatorRegistry.validate(\` call and trace
the variable assigned to the third element to confirm it — not the original — reaches
the API call.

### Schema definition ≠ schema registration

These are always two separate changes in two separate files. A PR is not complete
until both steps are verified. The unregistered-schema bug will not surface in test
runs unless a test explicitly calls the tool through the full validation path.

### Bounds on paired fields should mirror each other

When two fields are semantically paired (e.g., \`min_rssi\` / \`sens_level\`, both
representing RSSI thresholds in dBm), their \`minimum\`/\`maximum\` bounds should be
identical. Inconsistent bounds are confusing and likely wrong — cross-check during
schema review.

### Each app has its own registry class

\`UniFiValidatorRegistry\` (network), \`ProtectValidatorRegistry\` (protect). Registering
in the wrong app's \`validator_registry.py\` means the tool's app server never finds
the validator.

### Gotcha — validate() and validate_and_apply_defaults() both return 3-tuples, neither raises

Always unpack \`is_valid, error_msg, validated_data =\` and check \`if not is_valid:\`.
The \`validated_data\` is \`None\` on failure.

### Community PR mandatory gates

validator key present in \`_validators\`, correct method for the operation type (update vs
create), 3-tuple fully unpacked, and \`validated_data\` used downstream. Flag all four
before approving.
