# Firewall Policy Schema Reference

Complete schema reference for creating firewall policies via the unifi-network-mcp tools.

---

## Rulesets

Rulesets define the traffic direction and zone for a rule. Choose based on where traffic enters and exits.

| Ruleset | Description |
|---------|-------------|
| `WAN_IN` | Traffic entering from WAN, destined for LAN/local resources |
| `WAN_OUT` | Traffic leaving from LAN to WAN (outbound) |
| `WAN_LOCAL` | Traffic destined for the router itself from WAN |
| `LAN_IN` | Traffic entering from LAN (inbound to the router or forwarded) |
| `LAN_OUT` | Traffic leaving from the router to LAN (less common) |
| `LAN_LOCAL` | Traffic destined for the router itself from LAN |
| `GUEST_IN` | Traffic entering from the guest network |
| `GUEST_OUT` | Traffic leaving from the router to the guest network |
| `GUEST_LOCAL` | Traffic destined for the router itself from the guest network |
| `VPN_IN` | Traffic entering from VPN clients |
| `VPN_OUT` | Traffic leaving from the router to VPN clients |
| `VPN_LOCAL` | Traffic destined for the router itself from VPN |

**Choosing the right ruleset:**
- To block IoT from reaching the main LAN: use `LAN_IN` (traffic coming in from IoT, going to LAN)
- To block guest internet access at specific times: use `GUEST_IN`
- To block inbound WAN threats: use `WAN_IN`
- To restrict what clients can reach the router: use `LAN_LOCAL` or `GUEST_LOCAL`

---

## Actions

| Action | Behavior | When to Use |
|--------|----------|-------------|
| `accept` | Allow the traffic through | Explicit allow rules (before a broader block) |
| `drop` | Silently discard the packet (no response) | External-facing rules; avoids revealing firewall presence |
| `reject` | Discard and send RST (TCP) or ICMP unreachable (UDP/ICMP) | Internal rules; clients get immediate feedback instead of timing out |

**Recommendation:**
- Use `reject` for inter-VLAN blocking (IoT isolation, guest lockdown) — clients fail fast instead of hanging
- Use `drop` for WAN_IN rules blocking inbound external traffic

---

## Source / Destination Matching Targets

Both `source` and `destination` support the same matching options.

### By Zone

Match all traffic belonging to a firewall zone.

```json
{
  "type": "zone",
  "value": "<zone_id>"
}
```

Use `unifi_list_networks` to find zone IDs. Zones group multiple networks together.

### By Network / VLAN

Match traffic from a specific network or VLAN.

```json
{
  "type": "network_id",
  "value": "<network_id>"
}
```

Use `unifi_list_networks` to get network IDs. Preferred for per-VLAN rules.

### By Client MAC Address

Match specific devices by hardware address.

```json
{
  "type": "client_macs",
  "value": ["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"]
}
```

Use `unifi_get_clients` or `unifi_lookup_client_by_mac` to find MAC addresses.

### By IP Group

Match a named group of IP addresses or CIDR ranges.

```json
{
  "type": "ip_group_id",
  "value": "<ip_group_id>"
}
```

Use `unifi_list_firewall_groups` to find IP group IDs. Useful for maintaining shared address lists.

### By Geographic Region

Match traffic originating from or destined for a geographic region.

```json
{
  "type": "region",
  "value": "<region_code>"
}
```

Region codes follow ISO 3166-1 alpha-2 (e.g., `CN`, `RU`, `US`). Use for country-level blocking on WAN rules.

---

## Port Matching

| Mode | Description | Example |
|------|-------------|---------|
| `any` | Match all ports | `{"mode": "any"}` |
| `single_port` | Match one specific port | `{"mode": "single_port", "port": 443}` |
| `port_range` | Match a range of ports | `{"mode": "port_range", "port_start": 8000, "port_end": 9000}` |

Port matching applies to both source and destination. Most rules only need destination port matching.

---

## Protocols

| Value | Description |
|-------|-------------|
| `all` | Match all protocols (default for most rules) |
| `tcp` | TCP only (web, SSH, most application traffic) |
| `udp` | UDP only (DNS, streaming, VoIP) |
| `icmp` | ICMP only (ping, traceroute) |

---

## Connection States

Connection state matching refines rules to only apply to specific phases of a connection.

| State | Description | Common Use |
|-------|-------------|------------|
| `new` | First packet of a new connection | Block new connections while allowing established ones |
| `established` | Packets that are part of an established connection | Allow return traffic |
| `related` | Related to an existing connection (e.g., FTP data channel) | Allow related flows |
| `invalid` | Does not match any known connection state | Drop malformed/unknown traffic |

**Common pattern — stateful allow:**
```json
{
  "states": ["established", "related"]
}
```
This is often used at the top of a ruleset to allow return traffic before applying block rules.

---

## Schedule Format (Time-Based Rules)

Time-based rules activate and deactivate on a defined schedule.

```json
{
  "mode": "custom",
  "repeat_on_days": ["mon", "tue", "wed", "thu", "fri"],
  "time_all_day": false,
  "time_range_start": "22:00",
  "time_range_end": "06:00"
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `always`, `custom` | `always` = rule is always active; `custom` = schedule applies |
| `repeat_on_days` | `sun`, `mon`, `tue`, `wed`, `thu`, `fri`, `sat` | Days the rule is active |
| `time_all_day` | `true`, `false` | If true, the rule applies all day on selected days |
| `time_range_start` | `"HH:MM"` | Start time in 24-hour format (local controller time) |
| `time_range_end` | `"HH:MM"` | End time in 24-hour format |

Note: Time ranges that span midnight (e.g., 22:00–06:00) are supported.

---

## Simple vs Full Policy Creation

### `unifi_create_simple_firewall_policy` — Recommended for Most Requests

Accepts friendly names for networks, zones, and clients. The tool resolves names to IDs automatically.

**Use when:**
- Blocking one network from reaching another by name (e.g., "IoT" to "Main")
- Creating rules based on client names or hostnames
- User has provided network names, not raw IDs

**Example input:**
```json
{
  "name": "Block IoT from Main LAN",
  "ruleset": "LAN_IN",
  "action": "reject",
  "source_network": "IoT",
  "destination_network": "Main"
}
```

### `unifi_create_firewall_policy` — Full Control

Accepts raw controller IDs and the complete policy payload. No name resolution is performed.

**Use when:**
- `unifi_create_simple_firewall_policy` cannot express the required matching logic
- Working with IP groups, geographic regions, or complex port/protocol combinations
- Building rules programmatically from tool output (IDs already known)

**Example input:**
```json
{
  "name": "Block IoT from Main LAN",
  "ruleset": "LAN_IN",
  "action": "reject",
  "source": {"type": "network_id", "value": "64a1b2c3d4e5f6a7b8c9d0e1"},
  "destination": {"type": "network_id", "value": "64a1b2c3d4e5f6a7b8c9d0e2"},
  "protocol": "all",
  "enabled": true
}
```

---

## Useful Discovery Tools

Before creating policies, use these tools to gather required IDs:

| Tool | What It Returns |
|------|-----------------|
| `unifi_list_networks` | Network IDs, names, VLANs |
| `unifi_list_firewall_policies` | Existing policy IDs and current ruleset |
| `unifi_list_firewall_groups` | IP group and MAC group IDs |
| `unifi_get_clients` | Connected client MACs and hostnames |
| `unifi_get_dpi_stats` | Available DPI categories on this controller |
