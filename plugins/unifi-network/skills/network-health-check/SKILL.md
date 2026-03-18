---
name: network-health-check
description: Run a UniFi network health check — diagnose device status, connectivity issues, firmware updates, and system health. Use when asked to check network health, find what's down, diagnose connectivity issues, or get a network status summary.
---

# Network Health Check

## Setup Check

Before running a health check, verify the MCP server is configured:

- Check that `UNIFI_NETWORK_HOST` is set in the environment.
- If it is not set or the connection fails, stop and direct the user to `/setup` to configure the UniFi Network MCP server.
- Use `unifi_tool_index` to confirm available tools. If no UniFi tools are listed, the server is not connected.

## Quick Health Check (recommended)

Run `scripts/collect-health.py` for efficient, parallelized data gathering in a single pass.

**For machine-readable output (default for analysis):**
```bash
python scripts/collect-health.py --format json
```

**For human-readable output (default for display):**
```bash
python scripts/collect-health.py --format human
```

The script collects system info, network health, device list, and alarms in a single batched operation — significantly faster than sequential tool calls. Parse the output and proceed directly to reporting.

**Autonomous usage:** When running without user interaction, use `--format json` and interpret the structured output programmatically.

**Interactive usage:** When summarizing for a user, use `--format human` or convert the JSON output to the report format in the Report section below.

## Understanding Results

Use these reference documents to interpret collected data:

- `references/device-states.md` — maps device `state` integer codes to human-readable status (online, offline, isolated, etc.) and explains what each state means operationally.
- `references/alarm-types.md` — describes known alarm types, their severity levels, and recommended remediation steps for each.
- `references/health-subsystems.md` — explains the per-subsystem health fields returned by `unifi_get_network_health` (WAN, LAN, WLAN, VPN) and how to interpret `status` values.

Consult these references before classifying device states or alarm severity. Do not rely on assumptions — the UniFi state codes are not always intuitive.

## Manual Procedure (fallback)

Use this procedure when `scripts/collect-health.py` is not available or fails.

Run these checks in order. Use `unifi_batch` to parallelize independent queries.

### Step 1: System Overview (batch these together)

Call these tools via `unifi_batch`:
- `unifi_get_system_info` — controller version, uptime, CPU/memory
- `unifi_get_network_health` — per-subsystem health (WAN, LAN, WLAN, VPN)
- `unifi_list_devices` — all adopted devices with status
- `unifi_list_alarms` — active alarms

### Step 2: Analyze Device Status

From the device list, identify:
- **Offline devices** — any device with `state` != 1 (1 = connected). Check `references/device-states.md` for full state code meanings.
- **Devices needing updates** — check `upgradeable` field. Report current vs available firmware.
- **High-load devices** — check CPU/memory utilization if available in device stats.
- **Devices with poor uptime** — recently rebooted devices may indicate instability.

### Step 3: Client Health (if issues found or requested)

If devices are offline or network health shows issues:
- `unifi_list_clients` — connected client count, connection types
- `unifi_get_top_clients` — bandwidth hogs that might indicate problems

### Step 4: Alarm Review

For each active alarm:
- Classify severity using `references/alarm-types.md`
- Provide plain-language explanation of what it means
- Suggest remediation steps from the reference doc

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

- Always use `scripts/collect-health.py` or `unifi_batch` for initial data gathering — sequential tool calls are significantly slower.
- If `unifi_get_network_health` shows WAN health issues, that likely explains many downstream problems — lead with that finding.
- Don't overwhelm with data. Focus on what's broken or needs attention. A healthy network gets a brief "all clear" summary.
- Consult the reference docs before guessing at device state codes or alarm meanings — misclassification leads to bad recommendations.
- If the script exits with a connection error, fall back to the manual procedure and note the script failure in the report.
