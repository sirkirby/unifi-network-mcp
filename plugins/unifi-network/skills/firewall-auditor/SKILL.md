---
name: firewall-auditor
description: Audit UniFi firewall policies for conflicts, redundancies, security gaps, and best practices. Use when asked to review firewall rules, check for security issues, audit network policies, or optimize firewall configuration.
---

# Firewall Policy Auditor

You are auditing the firewall configuration on a UniFi network. Your goal is to identify conflicts, redundancies, security gaps, and deviations from best practices.

## Required MCP Server

This skill requires the `unifi-network` MCP server. Use `unifi_tool_index` to verify available tools, then `unifi_batch` to gather all data in parallel.

## Audit Procedure

### Step 1: Gather Data (batch all together)

Call via `unifi_batch`:
- `unifi_list_firewall_policies` — all policies
- `unifi_list_firewall_zones` — zone definitions
- `unifi_list_networks` — all networks/VLANs
- `unifi_list_ip_groups` — IP groups referenced by rules
- `unifi_get_dpi_stats` — DPI data (shows what traffic is actually flowing)

### Step 2: Policy Analysis

For each policy, extract and analyze:
- **Source/destination zones and networks**
- **Action** (ALLOW, REJECT, DROP)
- **Protocol/port specificity**
- **Enabled/disabled state**
- **Rule ordering** (higher priority rules shadow lower ones)

### Step 3: Check for Issues

**Conflicts:**
- Two rules matching the same traffic with different actions
- A broad ALLOW that undermines a specific REJECT (or vice versa, depending on order)

**Redundancies:**
- Rules that are strict subsets of other rules with the same action
- Disabled rules that duplicate enabled rules
- Rules targeting networks or groups that no longer exist

**Security gaps:**
- Inter-VLAN traffic allowed without explicit rules (check IoT → main network, guest → private)
- No egress filtering on high-risk VLANs (IoT devices should not reach everything)
- Missing rules for common best practices:
  - IoT VLAN should not access private networks
  - Guest VLAN should only access internet (not local resources)
  - Management VLAN should be restricted

**Unused rules:**
- Rules targeting IP groups with no members
- Rules for networks that have been deleted
- Rules that have been disabled for extended periods

### Step 4: Report

Present findings in this format:

```
## Firewall Audit Report

**Total Policies:** [count] ([enabled] enabled, [disabled] disabled)
**Zones:** [list]
**Networks:** [count]

### Critical Issues
[Issues that create security vulnerabilities]

### Warnings
[Redundancies, conflicts, or best practice violations]

### Recommendations
1. [Specific, actionable recommendation with which tool to use]
2. [...]

### Policy Summary Table
| # | Name | Action | Source | Destination | Status | Notes |
|---|------|--------|--------|-------------|--------|-------|
```

## Tips
- Focus on actionable findings. Don't report "everything is fine" items.
- When recommending changes, reference the specific tool and parameters needed (e.g., "Use `unifi_update_firewall_policy` with id=X to change action from ALLOW to REJECT").
- For complex environments (10+ policies), group findings by severity.
- If the user wants to act on recommendations, defer to the firewall-manager skill for execution.
