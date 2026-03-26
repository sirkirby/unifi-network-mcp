# Network Server Tool Reference (105 tools)

Complete reference for `unifi_*` tools. All read tools are always available. Mutating tools require permissions (see main skill for details).

## Table of Contents
- [Meta-Tools](#meta-tools)
- [Clients](#clients)
- [Devices](#devices)
- [Firewall](#firewall)
- [Networks & WLANs](#networks--wlans)
- [Port Forwarding](#port-forwarding)
- [QoS / Traffic Shaping](#qos--traffic-shaping)
- [Traffic Routes](#traffic-routes)
- [VPN](#vpn)
- [Routing](#routing)
- [MAC ACL Rules](#mac-acl-rules)
- [Events & Alarms](#events--alarms)
- [Statistics](#statistics)
- [Hotspot / Vouchers](#hotspot--vouchers)
- [User Groups](#user-groups)
- [System](#system)
- [Common Scenarios](#common-scenarios)

---

## Meta-Tools

Always available, regardless of registration mode.

| Tool | Purpose |
|------|---------|
| `unifi_tool_index` | List all available tools with full parameter schemas |
| `unifi_execute` | Execute any tool by name (essential in lazy mode) |
| `unifi_batch` | Run multiple tools in parallel |
| `unifi_batch_status` | Check status of an async batch job |

---

## Clients

<!-- AUTO:tools:clients -->
11 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_client_details` | Read | Returns the full raw client object for one client by MAC address — includes all controller-reported fields: IP, hostname, connection stat... |
| `unifi_list_blocked_clients` | Read | List clients/devices that are currently blocked from the network |
| `unifi_list_clients` | Read | Returns connected clients with MAC, name, hostname, IP, connection type (wired/wireless), and for wireless clients: SSID, signal dBm, cha... |
| `unifi_lookup_by_ip` | Read | Quick IP-to-hostname lookup. |
| `unifi_authorize_guest` | Mutate | Authorize a guest client to access the guest network by MAC address |
| `unifi_block_client` | Mutate | Block a client/device from the network by MAC address |
| `unifi_force_reconnect_client` | Mutate | Force a client to reconnect to the network (kick) by MAC address |
| `unifi_rename_client` | Mutate | Rename a client/device in the Unifi Network controller by MAC address |
| `unifi_set_client_ip_settings` | Mutate | Set fixed IP address and/or local DNS record for a client device. |
| `unifi_unauthorize_guest` | Mutate | Revoke authorization for a guest client by MAC address |
| `unifi_unblock_client` | Mutate | Unblock a previously blocked client/device by MAC address |
<!-- /AUTO:tools:clients -->

**Tips:**
- `unifi_lookup_by_ip` is the fastest way to find a specific client when you know its IP
- `unifi_list_clients` returns all currently connected clients — for historical, use events
- MAC addresses are the primary identifier for client operations (format: `AA:BB:CC:DD:EE:FF`)

---

## Devices

<!-- AUTO:tools:devices -->
8 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_device_details` | Read | Returns the full raw device object for one device by MAC address — includes radio tables, port tables, system stats, WAN info, firmware d... |
| `unifi_get_device_radio` | Read | Get radio configuration and live statistics for an access point. |
| `unifi_list_devices` | Read | Returns adopted device inventory with MAC, name, model, IP, firmware version, uptime, status (online/offline/upgrading/etc), device_categ... |
| `unifi_adopt_device` | Mutate | Adopt a pending device into the Unifi Network by MAC address |
| `unifi_reboot_device` | Mutate | Reboot a specific device by MAC address |
| `unifi_rename_device` | Mutate | Rename a device in the Unifi Network controller by MAC address |
| `unifi_update_device_radio` | Mutate | Update radio settings for a specific band on an access point. |
| `unifi_upgrade_device` | Mutate | Initiate a firmware upgrade for a device by MAC address (uses cached firmware by default) |
<!-- /AUTO:tools:devices -->

**Tips:**
- Pass `status='pending'` to `unifi_list_devices` to find devices waiting for adoption
- Rebooting interrupts service for connected clients — warn the user
- Radio changes affect all clients on that AP

---

## Firewall

<!-- AUTO:tools:firewall -->
9 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_firewall_policy_details` | Read | Get detailed configuration for a specific firewall policy by ID. |
| `unifi_list_firewall_policies` | Read | List firewall policies configured on the Unifi Network controller. |
| `unifi_list_firewall_zones` | Read | List controller firewall zones (V2 API). |
| `unifi_list_ip_groups` | Read | List IP groups configured on the controller (V2 API). |
| `unifi_create_firewall_policy` | Mutate | Create a new firewall policy with schema validation. |
| `unifi_create_simple_firewall_policy` | Mutate | Create a firewall policy using a simplified high-level schema. |
| `unifi_delete_firewall_policy` | Mutate | Delete a firewall policy by ID. |
| `unifi_toggle_firewall_policy` | Mutate | Enable or disable a specific firewall policy by ID. |
| `unifi_update_firewall_policy` | Mutate | Update specific fields of an existing firewall policy by ID. |
<!-- /AUTO:tools:firewall -->

**Tips:**
- Use `create_simple_firewall_policy` for straightforward block/allow rules
- Use `create_firewall_policy` when you need full control (protocol, ports, schedule, etc.)
- Always list existing policies first to understand current rule set before adding new ones
- Zone names come from `unifi_list_firewall_zones` — don't guess them

---

## Networks & WLANs

<!-- AUTO:tools:network -->
8 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_network_details` | Read | Get details for a specific network by ID. |
| `unifi_get_wlan_details` | Read | Get details for a specific WLAN by ID. |
| `unifi_list_networks` | Read | Returns all configured networks (LAN, WAN, VLAN-only) with name, purpose, IP subnet, VLAN ID, DHCP settings, and enabled state. |
| `unifi_list_wlans` | Read | List all configured Wireless LANs (WLANs) on the Unifi Network controller. |
| `unifi_create_network` | Mutate | Create a new network (LAN/VLAN) with schema validation. |
| `unifi_create_wlan` | Mutate | Create a new Wireless LAN (WLAN/SSID) with schema validation. |
| `unifi_update_network` | Mutate | Update specific fields of an existing network (LAN/VLAN). |
| `unifi_update_wlan` | Mutate | Update specific fields of an existing WLAN (SSID). |
<!-- /AUTO:tools:network -->

**Tips:**
- Network creation is disabled by default — requires `UNIFI_POLICY_NETWORK_NETWORKS_CREATE=true`
- WLAN creation similarly requires `UNIFI_POLICY_NETWORK_WLANS_CREATE=true`
- Networks and WLANs are related but separate: a WLAN connects to a network

---

## Port Forwarding

<!-- AUTO:tools:port_forwards -->
6 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_create_port_forward` | Read | Create a new port forwarding rule on your Unifi Network controller using schema validation. |
| `unifi_get_port_forward` | Read | Get a specific port forwarding rule by ID from your Unifi Network controller. |
| `unifi_list_port_forwards` | Read | List all port forwarding rules on your Unifi Network controller. |
| `unifi_create_simple_port_forward` | Mutate | Create a port forward using a simplified schema. |
| `unifi_toggle_port_forward` | Mutate | Toggle a port forwarding rule on or off on your Unifi Network controller. |
| `unifi_update_port_forward` | Mutate | Update specific fields of an existing port forwarding rule using schema validation. |
<!-- /AUTO:tools:port_forwards -->

---

## QoS / Traffic Shaping

<!-- AUTO:tools:qos -->
6 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_qos_rule_details` | Read | Get details for a specific QoS rule by ID. |
| `unifi_list_qos_rules` | Read | List all QoS rules on the Unifi Network controller for the current site. |
| `unifi_create_qos_rule` | Mutate | Create a new QoS rule on the Unifi Network controller. |
| `unifi_create_simple_qos_rule` | Mutate | Create a QoS rule using a simplified high-level schema. |
| `unifi_toggle_qos_rule_enabled` | Mutate | Enable or disable a specific QoS rule by ID. |
| `unifi_update_qos_rule` | Mutate | Update specific fields of an existing QoS rule. |
<!-- /AUTO:tools:qos -->

---

## Traffic Routes

<!-- AUTO:tools:traffic_routes -->
4 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_traffic_route_details` | Read | Get detailed information for a specific traffic route by ID. |
| `unifi_list_traffic_routes` | Read | List all traffic routes (policy-based routing rules) for the current site. |
| `unifi_toggle_traffic_route` | Mutate | Toggle a traffic route on/off by ID. |
| `unifi_update_traffic_route` | Mutate | Update a traffic route's settings. |
<!-- /AUTO:tools:traffic_routes -->

---

## VPN

<!-- AUTO:tools:vpn -->
6 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_vpn_client_details` | Read | Get details for a specific VPN client by ID. |
| `unifi_get_vpn_server_details` | Read | Get details for a specific VPN server by ID. |
| `unifi_list_vpn_clients` | Read | List all configured VPN clients (Wireguard, OpenVPN, etc). |
| `unifi_list_vpn_servers` | Read | List all configured VPN servers (Wireguard, OpenVPN, L2TP, etc). |
| `unifi_update_vpn_client_state` | Read | Enable or disable a specific VPN client by ID. |
| `unifi_update_vpn_server_state` | Read | Enable or disable a specific VPN server by ID. |
<!-- /AUTO:tools:vpn -->

**Tips:**
- VPN client mutations are enabled by default; VPN server mutations are disabled
- State changes take effect immediately — active tunnels will be disrupted

---

## Routing

<!-- AUTO:tools:routing -->
5 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_route_details` | Read | Get detailed information about a specific static route by its ID |
| `unifi_list_active_routes` | Read | List all active routes from the device routing table. |
| `unifi_list_routes` | Read | List all user-defined static routes for the current site. |
| `unifi_create_route` | Mutate | Create a new static route for advanced routing configuration. |
| `unifi_update_route` | Mutate | Update an existing static route's properties. |
<!-- /AUTO:tools:routing -->

---

## MAC ACL Rules

<!-- AUTO:tools:acl -->
5 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_acl_rule_details` | Read | Get detailed configuration for a specific MAC ACL rule by ID. |
| `unifi_list_acl_rules` | Read | List MAC ACL rules (Policy Engine) for Layer 2 access control. |
| `unifi_create_acl_rule` | Mutate | Create a new MAC ACL rule for Layer 2 access control within a VLAN. |
| `unifi_delete_acl_rule` | Mutate | Delete a MAC ACL rule. |
| `unifi_update_acl_rule` | Mutate | Update an existing MAC ACL rule. |
<!-- /AUTO:tools:acl -->

**Tips:**
- This is the only category with a delete tool — requires `UNIFI_POLICY_NETWORK_ACL_RULES_DELETE=true`

---

## Client Groups

<!-- AUTO:tools:client_groups -->
5 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_client_group_details` | Read | Get detailed configuration for a specific client group by ID. |
| `unifi_list_client_groups` | Read | List client groups (network member groups). |
| `unifi_create_client_group` | Mutate | Create a new client group (network member group). |
| `unifi_delete_client_group` | Mutate | Delete a client group. |
| `unifi_update_client_group` | Mutate | Update an existing client group. |
<!-- /AUTO:tools:client_groups -->

**Tips:**
- Client groups organize devices by MAC address for use in OON policies and firewall rules
- Delete requires `UNIFI_POLICY_NETWORK_CLIENT_GROUPS_DELETE=true`

---

## OON Policies

<!-- AUTO:tools:oon -->
6 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_oon_policy_details` | Read | Get detailed configuration for a specific OON policy by ID. |
| `unifi_list_oon_policies` | Read | List OON (Object-Oriented Network) policies. |
| `unifi_create_oon_policy` | Mutate | Create a new OON (Object-Oriented Network) policy. |
| `unifi_delete_oon_policy` | Mutate | Delete an OON policy. |
| `unifi_toggle_oon_policy` | Mutate | Toggle an OON policy on or off. |
| `unifi_update_oon_policy` | Mutate | Update an existing OON policy. |
<!-- /AUTO:tools:oon -->

**Tips:**
- OON policies control internet scheduling (bedtime blackouts), app blocking, QoS, and VPN routing
- Policies can target specific MACs (target_type=CLIENTS) or client groups (target_type=GROUPS)
- Use `unifi_toggle_oon_policy` for quick enable/disable without sending the full object
- Delete requires `UNIFI_POLICY_NETWORK_OON_POLICIES_DELETE=true`

---

## DPI Application Lookup

<!-- AUTO:tools:dpi -->
2 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_list_dpi_applications` | Read | List DPI applications available for use in firewall rules and OON policies. |
| `unifi_list_dpi_categories` | Read | List DPI application categories (e.g., 'Instant messengers', 'Peer-to-peer networks', 'Media streaming services'). |
<!-- /AUTO:tools:dpi -->

**Tips:**
- Requires `UNIFI_API_KEY` or `UNIFI_NETWORK_API_KEY` (official integration API)
- As of Network App 10.1.85, only categories 0-1 (IM, P2P) are populated (~2,100 apps)
- Categories 4+ (streaming, social media) are not yet available — add via UI and read back IDs
- Use `search` parameter on `unifi_list_dpi_applications` for name-based lookup

---

## Events & Alarms

<!-- AUTO:tools:events -->
5 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_event_types` | Read | Get a list of known event type prefixes for filtering events. |
| `unifi_list_alarms` | Read | Returns active alarms (security alerts, connectivity issues, firmware warnings). |
| `unifi_list_events` | Read | Returns timestamped event log entries (client connects/disconnects, device state changes, firmware updates, config changes) sorted newest... |
| `unifi_archive_alarm` | Mutate | Archive (resolve/dismiss) a specific alarm by its ID |
| `unifi_archive_all_alarms` | Mutate | Archive (resolve/dismiss) all active alarms |
<!-- /AUTO:tools:events -->

**Tips:**
- Use `unifi_get_event_types` first to understand what event types are available for filtering
- Events are the primary audit trail for network changes

---

## Statistics

<!-- AUTO:tools:stats -->
6 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_alerts` | Read | Get recent alerts from the Unifi Network controller |
| `unifi_get_client_stats` | Read | Get statistics for a specific client/device |
| `unifi_get_device_stats` | Read | Returns historical traffic time-series (rx/tx bytes, client counts) for one device by MAC or _id. |
| `unifi_get_dpi_stats` | Read | Get Deep Packet Inspection (DPI) statistics (applications and categories) |
| `unifi_get_network_stats` | Read | Get network statistics from the Unifi Network controller |
| `unifi_get_top_clients` | Read | Get a list of top clients by usage (sorted by total bytes) |
<!-- /AUTO:tools:stats -->

**Tips:**
- `unifi_get_top_clients` is the fastest way to find bandwidth hogs
- DPI stats show application-level breakdown (streaming, social media, gaming, etc.)
- Stats tools accept time range parameters for historical data

---

## Hotspot / Vouchers

<!-- AUTO:tools:hotspot -->
4 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_voucher_details` | Read | Get detailed information about a specific voucher by its ID |
| `unifi_list_vouchers` | Read | List all hotspot vouchers for the current site. |
| `unifi_create_voucher` | Mutate | Create hotspot voucher(s) for guest network access. |
| `unifi_revoke_voucher` | Mutate | Revoke/delete a hotspot voucher by its ID, preventing further use |
<!-- /AUTO:tools:hotspot -->

**Tips:**
- Vouchers are one-time or multi-use codes for guest captive portal
- You can set duration, bandwidth limits, and data quotas per voucher

---

## User Groups

<!-- AUTO:tools:usergroups -->
4 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_usergroup_details` | Read | Get detailed information about a specific user group by its ID |
| `unifi_list_usergroups` | Read | List all user groups (bandwidth profiles) for the current site. |
| `unifi_create_usergroup` | Mutate | Create a new user group (bandwidth profile) with optional speed limits. |
| `unifi_update_usergroup` | Mutate | Update an existing user group's name or bandwidth limits. |
<!-- /AUTO:tools:usergroups -->

---

## System

<!-- AUTO:tools:system,config -->
5 tools.

| Tool | Type | Description |
|------|------|-------------|
| `unifi_get_network_health` | Read | Returns per-subsystem health status for WAN, LAN, WLAN, and VPN — each with status, number of gateways/switches/APs, and active user counts. |
| `unifi_get_site_settings` | Read | Get current site settings (e.g., country code, timezone, connectivity monitoring). |
| `unifi_get_snmp_settings` | Read | Get current SNMP settings for the site (enabled state, community string). |
| `unifi_get_system_info` | Read | Returns controller version, uptime, hostname, memory/CPU usage, and update availability. |
| `unifi_update_snmp_settings` | Mutate | Update SNMP settings for the site (enable/disable, set community string). |
<!-- /AUTO:tools:system,config -->

**Tips:**
- `unifi_get_network_health` is the best "is everything OK?" check
- `unifi_get_system_info` tells you controller version and capabilities

---

## Common Scenarios

### "Who's eating all the bandwidth?"
1. `unifi_get_top_clients` → find the top bandwidth consumers
2. `unifi_get_client_details(mac="...")` → identify the device
3. `unifi_get_dpi_stats` → see what application categories are using bandwidth

### "Client can't connect to WiFi"
1. `unifi_list_clients` → see if client appears at all
2. `unifi_lookup_by_ip(ip="...")` → quick lookup if IP is known
3. `unifi_list_blocked_clients` → check if it's been blocked
4. `unifi_list_wlans` → verify SSID is active
5. `unifi_list_events` → look for connection failure events

### "Set up a guest network"
1. `unifi_list_networks` → see existing networks
2. `unifi_create_network(name="Guest", vlan_id=100, ...)` → create VLAN
3. `unifi_create_wlan(name="Guest WiFi", network_id="...", security="wpa2", ...)` → create SSID
4. `unifi_create_voucher(...)` → create access codes

### "Open a port for a game server"
1. `unifi_lookup_by_ip(ip="192.168.1.50")` → confirm the server is on the network
2. `unifi_create_simple_port_forward(name="Game Server", dst_port=25565, fwd_ip="192.168.1.50", ...)` → create rule
3. `unifi_list_firewall_policies` → verify no firewall rule blocks it

### "Network health check"
```
unifi_batch(tools=[
    {"tool": "unifi_get_system_info"},
    {"tool": "unifi_get_network_health"},
    {"tool": "unifi_list_devices"},
    {"tool": "unifi_get_alerts"},
    {"tool": "unifi_get_top_clients"}
])
```

### "What happened in the last hour?"
1. `unifi_list_events(start="<1 hour ago ISO>")` → recent events
2. `unifi_list_alarms` → any active alarms
3. `unifi_get_alerts` → system alerts
