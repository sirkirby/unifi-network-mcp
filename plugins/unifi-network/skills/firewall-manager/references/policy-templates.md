# Firewall Policy Templates

Pre-built policy recipes for common network security scenarios. Each template documents the goal, required parameters, tools to call, and expected outcome.

For machine-readable definitions, see `policy-templates.yaml`.

---

## Template 1: IoT Isolation

**Name:** `iot-isolation`

**Description:**
Blocks IoT devices from initiating connections to private/main LAN networks while still allowing them to reach the internet. This is the most common segmentation pattern for home and small office networks with smart devices, cameras, or home automation hubs.

**Why you need this:**
IoT devices are frequent targets for compromise. Once infected, they can be used to attack other devices on the same network. Isolating them to internet-only access limits the blast radius of a compromised device.

**Parameters required:**
- `iot_network` — Name of the IoT VLAN/network (e.g., "IoT", "Smart Home")
- `private_network` — Name of the main private network to protect (e.g., "Main", "Trusted")

**Tools to call:**
1. `unifi_list_networks` — confirm both networks exist and get their names
2. `unifi_create_simple_firewall_policy` — create the block rule

**Rule details:**
- Ruleset: `LAN_IN`
- Action: `reject`
- Source: IoT network
- Destination: Private/main network
- Protocol: `all`

**Expected outcome:**
IoT devices can reach the internet normally. Any attempt to connect to devices on the main LAN (printers, NAS, computers) is rejected immediately. Devices on the main LAN can still initiate connections to IoT devices if needed (e.g., a home automation hub on the main LAN polling sensors on IoT).

**Additional consideration:**
If you also want to prevent the main LAN from reaching IoT devices, create a second rule with source and destination swapped.

---

## Template 2: Guest Lockdown

**Name:** `guest-lockdown`

**Description:**
Restricts the guest Wi-Fi network to internet-only access, blocking all access to private LAN resources (NAS, printers, management interfaces, internal servers).

**Why you need this:**
Guest networks should never have access to internal resources. This rule enforces the separation even if the UniFi guest network isolation setting is misconfigured or bypassed.

**Parameters required:**
- `guest_network` — Name of the guest network (e.g., "Guest", "Visitor WiFi")
- `private_network` — Name of the private network(s) to protect

**Tools to call:**
1. `unifi_list_networks` — confirm network names
2. `unifi_create_simple_firewall_policy` — create the block rule

**Rule details:**
- Ruleset: `GUEST_IN`
- Action: `reject`
- Source: Guest network
- Destination: Private network
- Protocol: `all`

**Expected outcome:**
Guests can browse the internet freely. Any attempt to access internal IPs, printers, NAS shares, or router management pages is rejected. The rule does not affect internal devices reaching the internet through the guest network (there are none — only guests connect to that SSID).

---

## Template 3: Kids Content Filter

**Name:** `kids-content-filter`

**Description:**
Blocks access to social media and gaming platforms during specific hours (e.g., school nights, bedtime) for devices on a designated kids' VLAN. Uses DPI categories for application-aware blocking rather than port-based rules.

**Why you need this:**
Time-based parental controls allow full internet access during allowed hours while enforcing limits during study time, bedtime, or family time — without manual toggling.

**Parameters required:**
- `kids_network` — Name of the kids' VLAN (e.g., "Kids", "Children")
- `block_days` — Days to enforce the block (e.g., `["mon","tue","wed","thu","fri"]`)
- `block_start` — Block start time in 24-hour format (e.g., `"21:00"`)
- `block_end` — Block end time in 24-hour format (e.g., `"07:00"`)

**Tools to call:**
1. `unifi_list_networks` — confirm the kids' network exists
2. `unifi_get_dpi_stats` — get DPI category IDs for Social Media and Gaming on this controller
3. `unifi_create_firewall_policy` — create time-scheduled DPI-based block rules (one per category)

**Rule details (one rule per category):**
- Ruleset: `LAN_IN`
- Action: `reject`
- Source: Kids network
- Destination: `any`
- DPI category: Social Media (ID from `unifi_get_dpi_stats`)
- Schedule: custom, selected days, specified time range

**Expected outcome:**
During allowed hours, all internet access is unrestricted. During block hours on the selected days, attempts to open TikTok, Instagram, YouTube, Steam, or similar apps are rejected. Standard web browsing and school/homework sites remain accessible.

**Note:** DPI-based rules are more resilient than DNS blocking but can be bypassed by VPNs. Consider adding a VPN category block if needed.

---

## Template 4: Block BitTorrent

**Name:** `block-bittorrent`

**Description:**
Blocks BitTorrent and P2P file sharing traffic on a specific VLAN or across all VLANs. Uses DPI category-level blocking to catch all BitTorrent clients regardless of port.

**Why you need this:**
P2P traffic can consume significant bandwidth, expose the network to DMCA notices, and introduce malware via malicious torrents. Blocking at the DPI level is more effective than port blocking since modern clients use random ports.

**Parameters required:**
- `target_network` — Name of the network to restrict (or `any` for all networks)

**Tools to call:**
1. `unifi_get_dpi_stats` — get the DPI category ID for BitTorrent/P2P
2. `unifi_create_firewall_policy` — create the block rule with DPI category targeting

**Rule details:**
- Ruleset: `LAN_IN` (or `WAN_OUT` to block at the WAN boundary)
- Action: `drop`
- Source: Target network
- Destination: `any`
- DPI category: P2P / BitTorrent (ID from `unifi_get_dpi_stats`)

**Expected outcome:**
BitTorrent traffic is blocked at the firewall layer. Clients attempting to use torrent clients will see connections fail or stall. Regular downloads (HTTP/HTTPS), streaming, and gaming are unaffected.

---

## Template 5: Work VPN Split Tunnel

**Name:** `work-vpn-split-tunnel`

**Description:**
Allows devices on a work VLAN to route traffic through a corporate VPN while still accessing local LAN resources (printers, NAS, etc.) directly. Ensures work traffic goes through VPN while personal/local traffic bypasses it.

**Why you need this:**
Full-tunnel VPNs route all traffic through the corporate network, which is slow for local resources and puts unnecessary load on the corporate VPN gateway. Split tunneling allows work apps to use the VPN while local and streaming traffic takes the direct route.

**Parameters required:**
- `work_network` — Name of the work/corporate VLAN
- `vpn_interface` — VPN tunnel interface or VPN network name
- `corporate_subnets` — List of corporate IP ranges to route through VPN (e.g., `["10.0.0.0/8", "172.16.0.0/12"]`)

**Tools to call:**
1. `unifi_list_networks` — confirm network names and get IDs
2. `unifi_list_firewall_groups` — check for existing IP groups for corporate subnets
3. `unifi_create_firewall_policy` — create accept rules for corporate subnets via VPN, and allow local traffic directly

**Rule details:**
- Rule 1 (allow local): Ruleset `LAN_IN`, action `accept`, source: work network, destination: local RFC1918 ranges
- Rule 2 (route corporate via VPN): Ruleset `VPN_IN` or via routing policy, action `accept`, destination: corporate subnet IP group
- Rule 3 (default allow internet): Ruleset `LAN_IN`, action `accept`, source: work network, destination: `any`

**Expected outcome:**
Work devices can reach corporate resources through the VPN tunnel. Local resources (NAS, printers) are accessible directly without VPN overhead. Internet browsing goes direct rather than through the corporate proxy.

**Note:** Full split-tunnel configuration may also require static routes. Use `unifi_list_static_routes` to review existing routing configuration.

---

## Template 6: Camera Isolation

**Name:** `camera-isolation`

**Description:**
Locks IP cameras to only communicate with their designated NVR (Network Video Recorder) or cloud service. Blocks all other outbound traffic from camera devices, preventing data exfiltration or use of cameras as an attack pivot.

**Why you need this:**
IP cameras are among the most commonly compromised IoT devices. Many consumer cameras have poor firmware security and phone home to manufacturer servers in unexpected ways. This template enforces strict egress control so cameras can only reach their NVR and, optionally, a manufacturer cloud endpoint.

**Parameters required:**
- `camera_network` — Name of the camera VLAN (e.g., "Cameras", "Surveillance")
- `nvr_ip` — IP address of the NVR or recording server
- `allow_cloud` — Whether to allow manufacturer cloud access (`true`/`false`)
- `cloud_ip_group` — (if `allow_cloud` is true) IP group name for manufacturer cloud IPs

**Tools to call:**
1. `unifi_list_networks` — confirm camera network exists
2. `unifi_list_firewall_groups` — find or confirm NVR IP group
3. `unifi_create_simple_firewall_policy` — create accept rule for NVR traffic
4. `unifi_create_firewall_policy` — create drop-all rule as the final rule for the camera network

**Rule details:**
- Rule 1 (allow NVR): Ruleset `LAN_IN`, action `accept`, source: camera network, destination: NVR IP, protocol: `tcp/udp`
- Rule 2 (allow cloud, optional): Ruleset `WAN_OUT`, action `accept`, source: camera network, destination: cloud IP group
- Rule 3 (block all): Ruleset `LAN_IN`, action `drop`, source: camera network, destination: `any` (catch-all, lowest priority)

**Expected outcome:**
Cameras can send video streams to the NVR as normal. All other outbound connections (scanning the network, reaching unexpected internet endpoints) are silently dropped. If cloud access is disabled, cameras operate in fully local mode only.

**Important:** Rule order matters. The accept rules for NVR/cloud must have a lower rule number (higher priority) than the catch-all drop rule. Confirm rule ordering with `unifi_list_firewall_policies` after creation.
