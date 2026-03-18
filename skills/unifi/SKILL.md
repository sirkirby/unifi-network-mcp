---
name: unifi
description: How to work with UniFi infrastructure — networking, security cameras, and door access control. Use this skill when the user mentions UniFi, Ubiquiti, network management, WiFi configuration, firewall rules, VPN, security cameras, NVR, recordings, motion detection, door locks, visitor passes, or building access. Also use when troubleshooting connectivity for UniFi devices, reviewing security footage, managing physical access, or doing any kind of site audit across UniFi systems.
---

# UniFi MCP Server Guide

You have access to UniFi MCP servers that let you query and manage Ubiquiti UniFi infrastructure. There are three servers, each controlling a different domain. They can be used independently or together — a UniFi deployment may have any combination of these.

## The Three Servers

| Server | Tool Prefix | Domain | Tools | Maturity |
|--------|------------|--------|-------|----------|
| **Network** | `unifi_` | Networking: devices, clients, firewall, VPN, routing, WLANs, statistics | 91 | Stable |
| **Protect** | `protect_` | Physical security: cameras, NVR, recordings, smart detections, lights, sensors | 34 | Beta |
| **Access** | `access_` | Building access: doors, locks, credentials, visitors, access policies | 29 | Beta |

The tool prefix tells you which server a tool belongs to. If you see `unifi_*` tools, you have the Network server. If you see `protect_*`, you have Protect. If you see `access_*`, you have Access. You may have one, two, or all three.

### When to Use Each Server

**Network (`unifi_*`)** handles everything about the network itself:
- Who's connected? What's their IP/MAC/bandwidth? → clients tools
- What devices (APs, switches, gateways) are deployed? → devices tools
- Firewall rules, port forwards, traffic routes, QoS → firewall/routing tools
- VLANs, SSIDs, network configuration → network/wlan tools
- VPN tunnels and site-to-site → vpn tools
- Bandwidth stats, DPI data, top talkers → stats tools
- Guest WiFi vouchers → hotspot tools

**Protect (`protect_*`)** handles cameras and physical monitoring:
- What cameras are deployed? Are they recording? → cameras tools
- What motion/smart detections happened? → events tools
- Get a snapshot or RTSP stream URL → snapshot/stream tools
- Export a video clip for a time range → recordings tools
- Manage floodlights, sensors, chimes → devices tools
- Check NVR health and storage → system tools

**Access (`access_*`)** handles door and building entry control:
- What doors exist? Are they locked? → doors tools
- Lock or unlock a door → door mutation tools
- Who has access credentials (NFC/PIN/mobile)? → credentials tools
- Create time-bounded visitor passes → visitors tools
- What access policies and schedules are configured? → policies tools
- Who entered where and when? → events tools

## Tool Discovery — Start Here

All servers use **lazy loading** by default. Only a handful of meta-tools are registered initially — this saves ~96% of context tokens. The meta-tools follow the same pattern across all servers:

| Meta-Tool | Network | Protect | Access |
|-----------|---------|---------|--------|
| List all tools with schemas | `unifi_tool_index` | `protect_tool_index` | `access_tool_index` |
| Execute any tool by name | `unifi_execute` | `protect_execute` | `access_execute` |
| Run multiple tools in parallel | `unifi_batch` | `protect_batch` | `access_batch` |
| Check batch job status | `unifi_batch_status` | `protect_batch_status` | `access_batch_status` |

### Discovery Workflow

1. **Find the right tool** — call `*_tool_index` to see all available tools, organized by category with full parameter schemas. You don't need to guess tool names.

2. **Execute it** — In lazy mode, tools may not be directly callable. Use `*_execute` to call any tool by name:
   ```
   unifi_execute(tool_name="unifi_list_clients")
   protect_execute(tool_name="protect_list_cameras")
   access_execute(tool_name="access_list_doors")
   ```

3. **Batch for efficiency** — When you need multiple independent queries, batch them:
   ```
   unifi_batch(tools=[
       {"tool": "unifi_list_clients"},
       {"tool": "unifi_get_network_health"},
       {"tool": "unifi_list_devices"}
   ])
   ```
   This runs all three in parallel — significantly faster than sequential calls.

## Safety Model

These servers follow a "secure by default" philosophy. This matters because the tools control real infrastructure — network configuration, physical cameras, and door locks.

### Read Operations — Always Available

All `list_*`, `get_*`, and query tools work without special permissions. You can safely explore and report on the current state of any system.

### Mutations — Permission-Gated

Creating, updating, or deleting things requires explicit permission. The defaults vary by server because the risk profiles are different:

**Network** — Mixed defaults. Lower-risk mutations (firewall policies, port forwards, traffic routes, QoS rules, VPN clients, ACL rules, vouchers, user groups) are enabled by default. Higher-risk ones (networks, WLANs, devices, clients, routes, VPN servers) are disabled.

**Protect** — All mutations disabled by default. Changing camera settings, toggling recording, rebooting cameras — all require explicit opt-in. This is because Protect controls physical security hardware.

**Access** — All mutations disabled by default. Locking/unlocking doors, creating credentials, managing visitors — all need explicit permission. Mistakes here affect physical building security.

**Delete operations are always disabled by default** across every server and category.

If a mutation fails with a permission error, tell the user what environment variable to set. The pattern is:
```
UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>=true
```
Examples: `UNIFI_PERMISSIONS_CAMERAS_UPDATE=true`, `UNIFI_PERMISSIONS_DOORS_UPDATE=true`, `UNIFI_PERMISSIONS_NETWORKS_CREATE=true`

### Confirmation Flow — Preview Before Execute

Every state-changing tool uses a two-step pattern. This is a hard rule — the servers enforce it:

**Step 1: Preview** (default behavior)
```
unifi_create_network(name="Guest", vlan_id=100)
→ {"success": true, "requires_confirmation": true, "preview": {...}}
```

**Step 2: Confirm** (explicit opt-in)
```
unifi_create_network(name="Guest", vlan_id=100, confirm=true)
→ {"success": true, "data": {...}}
```

Always preview first, show the user what will change, and get their approval before confirming. The only exception is if the user explicitly tells you to skip previews, or if `UNIFI_AUTO_CONFIRM=true` is set (common in automation workflows).

## Response Format

All tools return a consistent structure:

```json
{"success": true, "data": <result>}
{"success": false, "error": "<specific, actionable message>"}
{"success": true, "requires_confirmation": true, "preview": <payload>}
```

Always check `success` before processing. Error messages include the operation that failed and what went wrong — relay these to the user rather than guessing at the cause.

## Efficiency Patterns

1. **Start with `*_tool_index`** to discover tools. Don't guess tool names — the index gives you exact names and schemas.

2. **Use `*_batch` for parallel reads.** If you need clients, devices, and health in one go, batch them. This is the single biggest efficiency win.

3. **Use filters.** Most `list_*` tools accept filter parameters (time range, type, ID). Use them to reduce response size rather than fetching everything and filtering client-side.

4. **Use `unifi_lookup_by_ip`** when you know the IP. It's faster than listing all clients and searching.

5. **Use `*_recent_events` for real-time data.** Protect and Access have websocket-backed event buffers that return instantly (no API call). Use these for "what just happened?" queries. Use `*_list_events` for historical lookups.

6. **Verify connectivity first.** If you're unsure whether a server is reachable, call `*_get_system_info` or `*_get_health` before attempting complex operations.

## Cross-Server Awareness

UniFi deployments often have Network, Protect, and Access running on the same hardware (UniFi OS Console). The systems share physical infrastructure:

- **Cameras and access readers are network clients.** If a camera goes offline in Protect, check its network status via Network tools. The device will appear as a client with a MAC address.
- **Door readers connect through the network.** Access device issues may be network issues. Cross-reference with `unifi_list_devices` or `unifi_lookup_by_ip`.
- **Events correlate across systems.** A person detected by Protect may have a corresponding door access event in Access. Timestamps let you correlate.

When troubleshooting, think about which layer the problem is at — network connectivity (Network server), application behavior (Protect/Access), or physical hardware.

## Per-Server Tool References

For complete tool listings organized by category, common scenarios, and usage tips, read the relevant reference file:

- `references/network-tools.md` — All 91 Network tools across 15 categories
- `references/protect-tools.md` — All 34 Protect tools across 7 categories
- `references/access-tools.md` — All 29 Access tools across 7 categories
- `references/cross-server-scenarios.md` — Multi-server workflows and correlation patterns
- `references/setup-and-configuration.md` — Installation, env vars, permissions, transport, troubleshooting

Read the reference file for the server you're working with. For cross-server tasks, read the scenarios reference. For setup or configuration questions, read the configuration reference.

## Access Server: Dual Authentication

Access has a unique dual-auth system worth knowing about:

- **API key path (port 12445)** — Used for read-only queries (listing doors, events, devices)
- **Local proxy session (port 443)** — Required for mutations (lock/unlock, create credentials, manage visitors)

If a mutation returns an auth error, the user may need to configure proxy session credentials (`UNIFI_ACCESS_USERNAME` + `UNIFI_ACCESS_PASSWORD`) in addition to or instead of an API key. Tools that require the proxy session say so in their description.

## Quick Decision Tree

```
User asks about...
├── WiFi, clients, bandwidth, IPs, MACs → Network (unifi_*)
├── Firewall, port forwarding, VPN, routing → Network (unifi_*)
├── Switches, APs, gateways, firmware → Network (unifi_*)
├── Cameras, recordings, snapshots, NVR → Protect (protect_*)
├── Motion detection, person/vehicle alerts → Protect (protect_*)
├── Floodlights, sensors, chimes → Protect (protect_*)
├── Doors, locks, building entry → Access (access_*)
├── Visitor passes, credentials, NFC/PIN → Access (access_*)
├── Access policies, schedules → Access (access_*)
├── "Is X online?" → Depends: Network for connectivity, Protect/Access for app status
├── "What happened at <time>?" → Check events on all relevant servers
└── "Site overview" → Batch system_info + health on all available servers
```
