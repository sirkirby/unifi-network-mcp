# Network Health Subsystems Reference

## Subsystems

`unifi_get_network_health` returns one object per subsystem.

| Subsystem | Key Fields | What It Tells You |
|-----------|-----------|-------------------|
| `wan` | `status`, `num_gw`, latency, uptime, ISP info | Internet connectivity health |
| `lan` | `status`, `num_sw`, port errors | Switch and wired network health |
| `wlan` | `status`, `num_ap`, channel utilization | Wireless network health |
| `vpn` | `status`, tunnel count | VPN tunnel connectivity |

## Status Values

| Status | Meaning |
|--------|---------|
| `ok` | Subsystem healthy — all devices responding |
| `warning` | Degraded — some devices or links unhealthy |
| `error` | Subsystem down or critical issues |
| `unknown` | Cannot determine status |

## Diagnostic Priority Order

Always check in this order — upstream failures explain downstream symptoms:

1. **WAN first** — if WAN is down, everything internet-dependent fails
2. **LAN (switches)** — if switches are down, APs and wired clients lose connectivity
3. **WLAN** — AP-specific issues (interference, overload, firmware)
4. **VPN** — site-to-site and remote access tunnels

## System Info Fields

`unifi_get_system_info` returns a raw dict from `/stat/sysinfo`:
- `version` — Controller firmware version
- `uptime` — Controller uptime (seconds)
- Hostname, CPU/memory stats, update availability (controller-dependent)

## Quick Health Assessment

| Scenario | Priority | Likely Cause |
|----------|----------|-------------|
| WAN error, everything else warning | P1 | ISP outage or gateway failure |
| LAN error, WLAN warning | P1 | Core switch down, APs lose uplink |
| WLAN warning, rest ok | P2 | AP interference, overload, or firmware issue |
| All ok, alarms present | P3 | Resolved issues or informational events |
| VPN error, rest ok | P2 | Tunnel configuration or remote site issue |
