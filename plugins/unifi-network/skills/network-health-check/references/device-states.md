# Device States Reference

## State Codes

| Code | Label | Description |
|------|-------|-------------|
| 0 | offline | Device not communicating with controller |
| 1 | online | Connected and functioning normally |
| 2 | pending_adoption | Discovered but not yet adopted |
| 4 | adopting | Being adopted or managed by another controller |
| 5 | provisioning | Applying configuration changes |
| 6 | upgrading | Performing firmware upgrade |
| 11 | heartbeat_missed | Missed heartbeat — may be rebooting or unreachable |

**Key rule:** State 1 = healthy. Any other state for an adopted device = investigate.

## Device Type Prefixes

| API Prefix | Type | Filter Keyword |
|------------|------|---------------|
| `uap` | Access Point | `ap` |
| `usw`, `usk` | Switch | `switch` |
| `ugw`, `udm`, `uxg` | Gateway / Dream Machine | `gateway` |
| `usp` | Smart Power (PDU) | `pdu` |

### Important: Smart Power Strips vs Access Points

UniFi Smart Power strips (model UP6, UP1) connect wirelessly via mesh and report as `uap` type in the API — but they are NOT access points.

**The definitive field is `is_access_point`** (boolean) in the device object. The MCP tool's `device_category` field uses this to correctly classify devices:
- `device_category: "ap"` → real access point (`is_access_point: true`)
- `device_category: "pdu"` → power strip or PDU (`is_access_point: false` despite `type: uap`)

**When counting APs, use the `device_category` field, not the `type` field.** The `unifi_list_devices` filter `device_type=ap` already uses this classification and will exclude power strips.

Known power strip models: UP6 (6-outlet strip), UP1 (single plug). These have `is_access_point: false`, mesh uplinks, and no `vap_table`.

## Radio Band Codes

| API Code | Band |
|----------|------|
| `ng` | 2.4 GHz |
| `na` | 5 GHz |
| `6e` | 6 GHz (WiFi 6E) |

## Device Response Fields

**Base fields** (always returned by `unifi_list_devices`):
`mac`, `name`, `model`, `type`, `device_category`, `ip`, `status`, `uptime`, `last_seen`, `firmware`, `upgradable`, `adopted`, `connection_network`, `uplink`, `load_avg_1`, `mem_pct`, `model_eol`, `_id`

| Field | Type | Description |
|-------|------|-------------|
| `device_category` | string | Semantic category: `ap`, `switch`, `gateway`, `pdu`, `wan`, `unknown` |
| `upgradable` | bool | True if firmware update is available |
| `connection_network` | string | Name of the VLAN/network the device is connected to |
| `uplink` | object | Topology: `{type, speed, uplink_device, uplink_port}` |
| `load_avg_1` | float | 1-minute load average (null if unavailable) |
| `mem_pct` | float | Memory usage percentage (null if unavailable) |
| `model_eol` | bool | True if the device model is end-of-life |

**Extended fields** (with `include_details=true`):
`serial`, `hw_revision`, `model_display`, `clients`

**Type-specific fields:**

| Type | Additional Fields |
|------|------------------|
| AP | `radio_table`, `vap_table`, `wifi_bands`, `experience_score`, `num_clients` |
| Switch | `ports`, `total_ports`, `num_clients`, `poe_info` (current, power, voltage) |
| Gateway | `wan1`, `wan2`, `num_clients`, `network_table`, `system_stats`, `speedtest_status` |
