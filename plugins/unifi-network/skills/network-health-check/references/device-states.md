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

UniFi Smart Power strips (USP-Strip, USP-Plug, USP-RPS) connect wirelessly via mesh and may appear as `uap` type devices in the API. **Do NOT count these as access points.** Identify them by:

- **Model string:** contains `UP1`, `UP6`, `USP`, `USPRPS`, or similar power-related model codes
- **Name pattern:** often named "Power-*" or contain "UPS", "PDU", "Power Strip"
- **Uplink type:** shows "Meshing" (wireless mesh) rather than a wired Ethernet uplink
- **No radio_table or vap_table:** power strips do not serve wireless clients

When counting APs, **exclude** any device whose `model` or `name` indicates it is a power strip or UPS. Use `unifi_list_devices` with `device_type=pdu` to get power devices separately, but note this filter uses `usp` prefix and may miss power strips that report as `uap`.

**For accurate AP counts:** Filter `unifi_list_devices` with `device_type=ap`, then exclude any device whose name contains "Power", "UPS", or "PDU", or whose model does not match known AP models (U6, U7, UAP, nanoHD, FlexHD, etc.).

## Radio Band Codes

| API Code | Band |
|----------|------|
| `ng` | 2.4 GHz |
| `na` | 5 GHz |
| `6e` | 6 GHz (WiFi 6E) |

## Device Response Fields

**Base fields** (always returned by `unifi_list_devices`):
`mac`, `name`, `model`, `type`, `ip`, `status`, `uptime`, `last_seen`, `firmware`, `adopted`, `_id`

**Extended fields** (with `include_details=true`):
`serial`, `hw_revision`, `model_display`, `clients`

**Type-specific fields:**

| Type | Additional Fields |
|------|------------------|
| AP | `radio_table`, `vap_table`, `wifi_bands`, `experience_score`, `num_clients` |
| Switch | `ports`, `total_ports`, `num_clients`, `poe_info` (current, power, voltage) |
| Gateway | `wan1`, `wan2`, `num_clients`, `network_table`, `system_stats`, `speedtest_status` |
