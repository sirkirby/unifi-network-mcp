# Tool Catalog

The UniFi Network MCP server exposes 91 tools, all prefixed with `unifi_`. Read-only tools are always available. Mutating tools are controlled by the [permission system](permissions.md).

For machine-readable tool metadata, call the `unifi_tool_index` meta-tool at runtime, or inspect `src/unifi_network_mcp/tools_manifest.json`.

## Meta-Tools

These are always registered regardless of mode:

- `unifi_tool_index` — List all available tools with schemas
- `unifi_execute` — Execute a tool by name (for lazy/meta_only modes)
- `unifi_batch` — Execute multiple tools in parallel
- `unifi_batch_status` — Check batch job status

## Firewall (8 tools)

- `unifi_list_firewall_policies` — List all firewall policies
- `unifi_get_firewall_policy_details` — Get policy details by ID
- `unifi_toggle_firewall_policy` — Enable/disable a policy
- `unifi_create_firewall_policy` — Create with full schema validation
- `unifi_create_simple_firewall_policy` — Create with simplified schema
- `unifi_update_firewall_policy` — Update policy fields
- `unifi_list_firewall_zones` — List firewall zones (V2 API)
- `unifi_list_ip_groups` — List IP groups (V2 API)

## MAC ACL Rules (5 tools)

- `unifi_list_acl_rules` — List MAC ACL rules, optionally filtered by network/VLAN
- `unifi_get_acl_rule_details` — Get rule details by ID
- `unifi_create_acl_rule` — Create a Layer 2 access control rule
- `unifi_update_acl_rule` — Update an existing rule
- `unifi_delete_acl_rule` — Delete a rule (requires delete permission)

## Traffic Routes (6 tools)

- `unifi_list_traffic_routes` — List policy-based routing rules
- `unifi_get_traffic_route_details` — Get route details by ID
- `unifi_toggle_traffic_route` — Enable/disable a route
- `unifi_create_traffic_route` — Create with full schema
- `unifi_create_simple_traffic_route` — Create with simplified schema
- `unifi_update_traffic_route` — Update route settings

## Port Forwarding (6 tools)

- `unifi_list_port_forwards` — List all port forwarding rules
- `unifi_get_port_forward` — Get rule details by ID
- `unifi_toggle_port_forward` — Enable/disable a rule
- `unifi_create_port_forward` — Create with full schema validation
- `unifi_create_simple_port_forward` — Create with simplified schema
- `unifi_update_port_forward` — Update rule fields

## QoS / Traffic Shaping (6 tools)

- `unifi_list_qos_rules` — List all QoS rules
- `unifi_get_qos_rule_details` — Get rule details by ID
- `unifi_toggle_qos_rule_enabled` — Enable/disable a rule
- `unifi_create_qos_rule` — Create with full schema
- `unifi_create_simple_qos_rule` — Create with simplified schema
- `unifi_update_qos_rule` — Update rule fields

## Networks & WLANs (8 tools)

- `unifi_list_networks` — List all networks (LAN, WAN, VLAN)
- `unifi_get_network_details` — Get network details by ID
- `unifi_create_network` — Create a network (LAN/VLAN)
- `unifi_update_network` — Update network fields
- `unifi_list_wlans` — List all wireless LANs
- `unifi_get_wlan_details` — Get WLAN details by ID
- `unifi_create_wlan` — Create a WLAN/SSID
- `unifi_update_wlan` — Update WLAN fields

## VPN (6 tools)

- `unifi_list_vpn_clients` — List VPN clients (WireGuard, OpenVPN)
- `unifi_get_vpn_client_details` — Get client details by ID
- `unifi_update_vpn_client_state` — Enable/disable a VPN client
- `unifi_list_vpn_servers` — List VPN servers
- `unifi_get_vpn_server_details` — Get server details by ID
- `unifi_update_vpn_server_state` — Enable/disable a VPN server

## Devices (8 tools)

- `unifi_list_devices` — List all adopted devices
- `unifi_get_device_details` — Get full device object by MAC
- `unifi_get_device_radio` — Get AP radio config and stats
- `unifi_update_device_radio` — Update radio settings (TX power, channel, width)
- `unifi_reboot_device` — Reboot a device by MAC
- `unifi_rename_device` — Rename a device by MAC
- `unifi_adopt_device` — Adopt a pending device
- `unifi_upgrade_device` — Initiate firmware upgrade

## Clients (11 tools)

- `unifi_list_clients` — List connected clients
- `unifi_get_client_details` — Get full client object by MAC
- `unifi_lookup_by_ip` — Quick IP-to-hostname lookup
- `unifi_list_blocked_clients` — List blocked clients
- `unifi_block_client` — Block a client by MAC
- `unifi_unblock_client` — Unblock a client by MAC
- `unifi_rename_client` — Rename a client by MAC
- `unifi_force_reconnect_client` — Kick a client to force reconnection
- `unifi_authorize_guest` — Authorize a guest client
- `unifi_unauthorize_guest` — Revoke guest authorization
- `unifi_set_client_ip_settings` — Set fixed IP / local DNS record

## Events & Alarms (5 tools)

- `unifi_list_events` — List timestamped event log entries
- `unifi_list_alarms` — List active alarms
- `unifi_archive_alarm` — Archive a specific alarm
- `unifi_archive_all_alarms` — Archive all active alarms
- `unifi_get_event_types` — Get known event type prefixes

## Routing (5 tools)

- `unifi_list_routes` — List user-defined static routes
- `unifi_get_route_details` — Get route details by ID
- `unifi_create_route` — Create a static route
- `unifi_update_route` — Update a static route
- `unifi_list_active_routes` — List active routes from device routing table

## Hotspot / Vouchers (4 tools)

- `unifi_list_vouchers` — List all hotspot vouchers
- `unifi_get_voucher_details` — Get voucher details by ID
- `unifi_create_voucher` — Create guest network voucher(s)
- `unifi_revoke_voucher` — Revoke a voucher (requires delete permission)

## User Groups (4 tools)

- `unifi_list_usergroups` — List bandwidth profiles
- `unifi_get_usergroup_details` — Get group details by ID
- `unifi_create_usergroup` — Create a bandwidth profile
- `unifi_update_usergroup` — Update group settings

## Statistics (6 tools)

- `unifi_get_network_stats` — Network-wide statistics
- `unifi_get_client_stats` — Per-client statistics
- `unifi_get_device_stats` — Per-device traffic time-series
- `unifi_get_top_clients` — Top clients by bandwidth usage
- `unifi_get_dpi_stats` — Deep Packet Inspection statistics
- `unifi_get_alerts` — Recent alerts

## System (5 tools)

- `unifi_get_system_info` — Controller version, uptime, resource usage
- `unifi_get_network_health` — Per-subsystem health (WAN, LAN, WLAN, VPN)
- `unifi_get_site_settings` — Current site settings
- `unifi_get_snmp_settings` — SNMP configuration
- `unifi_update_snmp_settings` — Update SNMP settings

## Tool Registration Modes

| Mode | Initial Tokens | Behavior |
|------|---------------|----------|
| `lazy` (default) | ~200 | Meta-tools registered; others load on first use |
| `eager` | ~5,000 | All tools registered immediately |
| `meta_only` | ~200 | Only meta-tools; use `unifi_execute` for everything |

Set via `UNIFI_TOOL_REGISTRATION_MODE`. Lazy mode is recommended for LLM clients.
