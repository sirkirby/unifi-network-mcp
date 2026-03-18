# Alarm & Event Types Reference

## Event Type Prefixes

Use with `unifi_list_events` `event_type` filter parameter.

| Prefix | Category | Examples |
|--------|----------|----------|
| `EVT_SW_` | Switch | Connected, Lost_Contact, STP changes, port events |
| `EVT_AP_` | Access Point | Connected, Lost_Contact, channel changes, radar detected |
| `EVT_GW_` | Gateway | WAN transitions, failover, firmware updates |
| `EVT_LAN_` | LAN | New device, IP conflict, DHCP events |
| `EVT_WU_` | WLAN User | Client connect, disconnect, roam |
| `EVT_WG_` | WLAN Guest | Guest client events |
| `EVT_IPS_` | IPS/IDS | Blocked threats, anomalous traffic, security alerts |
| `EVT_AD_` | Admin | Login, configuration changes, firmware updates |
| `EVT_DPI_` | DPI | Deep Packet Inspection events |

## Alarm Severity Levels

| Severity | Meaning | Action |
|----------|---------|--------|
| `critical` | Service-impacting, immediate attention needed | Investigate now |
| `warning` | Potential issue or degraded state | Review and plan |
| `informational` | Notable event, no action needed | Note for awareness |

## Common Alarms and What They Mean

| Type | Severity | What It Means | What To Do |
|------|----------|---------------|-----------|
| `EVT_AP_Lost_Contact` | critical | AP stopped responding | Check power and uplink connectivity |
| `EVT_AP_Connected` | info | AP came back online | Verify clients reconnected |
| `EVT_SW_Lost_Contact` | critical | Switch offline | Check power, uplink, STP topology |
| `EVT_SW_Connected` | info | Switch back online | Verify ports and VLANs recovered |
| `EVT_GW_WANTransition` | warning | WAN failover or recovery | Check ISP status, failover config |
| `EVT_IPS_*` | varies | Security event detected | Review threat details, check source |

## Response Fields

**Alarms** (`unifi_list_alarms`): `_id`, `msg`, `severity`, `type`, `timestamp`, device/client MAC

**Events** (`unifi_list_events`): `_id`, `msg`, `time` (Unix timestamp), `type`
