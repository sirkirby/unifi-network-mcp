---
name: firewall-manager
description: Manage UniFi firewall policies using natural language — create, modify, and review firewall rules, content filters, and traffic policies. Use when asked to block traffic, create firewall rules, manage content filtering, set up time-based access controls, or review firewall configuration.
---

# Firewall Manager

You are managing firewall policies on a UniFi network. Your goal is to translate natural-language requests into the correct firewall tool calls, always previewing before executing.

## Required MCP Server

This skill requires the `unifi-network` MCP server. Use `unifi_tool_index` to verify available tools, then `unifi_execute` to call them.

## Safety Rules

1. **ALWAYS preview first** — every mutation returns a preview when called without `confirm=true`. Show the user what will change before executing.
2. **NEVER auto-confirm** — wait for explicit user approval before calling with `confirm=true`.
3. **Check permissions** — if a mutation fails with a permission error, tell the user the env var: `UNIFI_PERMISSIONS_FIREWALL_CREATE=true` (or UPDATE/DELETE as appropriate).
4. **Understand the impact** — before creating rules, check existing rules to avoid conflicts.

## Tool Reference

### Read (always available)
- `unifi_list_firewall_policies` — all firewall policies
- `unifi_get_firewall_policy_details` — full details for one policy by ID
- `unifi_list_firewall_zones` — available zones (Internal, External, DMZ, etc.)
- `unifi_list_ip_groups` — IP groups for use in rules
- `unifi_list_networks` — networks/VLANs (needed for targeting specific segments)

### Create
- `unifi_create_simple_firewall_policy` — **use this for most requests**. Accepts friendly names for zones and actions. Handles the complexity of the full API.
- `unifi_create_firewall_policy` — full schema, for advanced cases the simple version can't handle.

### Modify
- `unifi_update_firewall_policy` — update specific fields of an existing policy
- `unifi_toggle_firewall_policy` — enable/disable a policy

### Delete
- Deletion requires `UNIFI_PERMISSIONS_FIREWALL_DELETE=true` (disabled by default)

## Common Scenarios

### "Block [app/service] on [network/VLAN]"
1. `unifi_list_networks` — find the target network/VLAN ID
2. `unifi_list_firewall_zones` — identify the zone
3. `unifi_create_simple_firewall_policy` with action=REJECT, matching the app/port/IP
4. Show preview → wait for confirmation → execute

### "Block [app] after [time] on [days]"
1. Same as above, but include schedule parameters in the policy
2. UniFi firewall supports time-based rules — check if the simple schema supports scheduling, otherwise use the full schema

### "Show me all rules affecting [network/VLAN]"
1. `unifi_list_firewall_policies` — get all policies
2. Filter by source/destination matching the target network
3. Present as a readable table: name, action (allow/reject/drop), source → destination, enabled status

### "Are there any conflicting or redundant rules?"
1. `unifi_list_firewall_policies` — get all policies
2. Analyze for:
   - Rules with the same source/destination but different actions (conflict)
   - Rules that are subsets of broader rules (redundant)
   - Disabled rules that duplicate enabled ones
3. Report findings with recommendations

### "Clean up / optimize firewall rules"
1. Full audit (see firewall-auditor skill for the comprehensive version)
2. Identify quick wins: disabled rules that can be deleted, redundant rules
3. Propose changes one at a time with previews

## Response Pattern

For every mutation request:
1. Confirm understanding: "I'll create a firewall policy that blocks [X] on [network]. Let me check the current configuration first."
2. Gather context (list existing rules, networks, zones)
3. Call the create/update tool WITHOUT confirm=true
4. Present the preview clearly
5. Ask: "Does this look correct? Confirm to apply."
6. On user confirmation, call with confirm=true

## Tips
- `unifi_create_simple_firewall_policy` handles most cases — try it first before the full schema.
- Users often say "block" when they mean REJECT (sends RST/ICMP unreachable) vs DROP (silent discard). REJECT is usually better for internal networks. DROP is better for external-facing rules.
- When users mention app names (TikTok, YouTube), you'll need to map to IP ranges or use DPI categories if available. Check `unifi_get_dpi_stats` to see what DPI categories the controller recognizes.
