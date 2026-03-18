---
name: network-health-check
description: Run a UniFi network health check — diagnose device status, connectivity issues, firmware updates, and system health. Use when asked to check network health, find what's down, diagnose connectivity issues, or get a network status summary.
---

# Network Health Check

You are performing a health check on a UniFi network. Your goal is to identify issues, summarize status, and provide actionable recommendations.

## Required MCP Server

This skill requires the `unifi-network` MCP server. Use `unifi_tool_index` to verify available tools, then `unifi_execute` or `unifi_batch` to call them.

## Health Check Procedure

Run these checks in order. Use `unifi_batch` to parallelize independent queries.

### Step 1: System Overview (batch these together)

Call these tools via `unifi_batch`:
- `unifi_get_system_info` — controller version, uptime, CPU/memory
- `unifi_get_network_health` — per-subsystem health (WAN, LAN, WLAN, VPN)
- `unifi_list_devices` — all adopted devices with status
- `unifi_list_alarms` — active alarms

### Step 2: Analyze Device Status

From the device list, identify:
- **Offline devices** — any device with `state` != 1 (1 = connected). Report name, model, MAC, last seen time.
- **Devices needing updates** — check `upgradeable` field. Report current vs available firmware.
- **High-load devices** — check CPU/memory utilization if available in device stats.
- **Devices with poor uptime** — recently rebooted devices may indicate instability.

### Step 3: Client Health (if issues found or requested)

If devices are offline or network health shows issues:
- `unifi_list_clients` — connected client count, connection types
- `unifi_get_top_clients` — bandwidth hogs that might indicate problems

### Step 4: Alarm Review

For each active alarm:
- Classify severity (critical / warning / informational)
- Provide plain-language explanation of what it means
- Suggest remediation steps

### Step 5: Report

Present findings in this format:

```
## Network Health Report

**Overall Status:** [Healthy / Warning / Critical]
**Controller:** [version] — uptime [X days]

### Devices ([online]/[total])
- [List any offline or problematic devices]
- [List devices needing firmware updates]

### Active Alarms ([count])
- [Summarize each alarm with severity and recommendation]

### Recommendations
1. [Actionable item]
2. [Actionable item]
```

## Tips
- Always use `unifi_batch` for the initial data gathering — it's significantly faster than sequential calls.
- If `unifi_get_network_health` shows WAN health issues, that likely explains many downstream problems — lead with that finding.
- Don't overwhelm with data. Focus on what's broken or needs attention. A healthy network gets a brief "all clear" summary.
