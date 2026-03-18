# Cross-Server Scenarios

These scenarios involve coordinating across multiple UniFi MCP servers. They represent real-world tasks where the network, camera, and access systems intersect.

## Table of Contents
- [How the Systems Connect](#how-the-systems-connect)
- [Security Incident Investigation](#security-incident-investigation)
- [Device Connectivity Troubleshooting](#device-connectivity-troubleshooting)
- [Full Site Health Check](#full-site-health-check)
- [New Employee Onboarding](#new-employee-onboarding)
- [Visitor Management (End-to-End)](#visitor-management-end-to-end)
- [After-Hours Activity Audit](#after-hours-activity-audit)
- [Emergency Lockdown](#emergency-lockdown)
- [Device Inventory Across Systems](#device-inventory-across-systems)

---

## How the Systems Connect

All three systems share the same physical infrastructure:

```
Physical Building
├── Network (unifi_*)
│   ├── Switches, APs, Gateway — the backbone
│   ├── Cameras appear as network clients (MAC/IP)
│   └── Access readers/hubs appear as network clients (MAC/IP)
├── Protect (protect_*)
│   ├── NVR manages cameras — depends on Network for connectivity
│   ├── Smart detections (person, vehicle) — visual layer
│   └── Sensors (motion, door, temp, leak) — environmental layer
└── Access (access_*)
    ├── Door locks, readers, intercoms — physical entry control
    ├── Credentials (NFC/PIN/mobile) — identity layer
    └── Policies + schedules — authorization layer
```

**Key relationship:** Protect cameras and Access readers are clients on the Network. When they go offline in their application, the root cause is often a network issue visible via Network tools.

**Event correlation:** Timestamps let you correlate events across systems. A person detected at 10:03 by Protect may match a door unlock at 10:03 in Access, and a new client connection at 10:02 in Network.

---

## Security Incident Investigation

**Scenario:** Something suspicious happened at a specific time and location. Investigate across all available data.

### Step 1: Gather events from all systems in parallel
```
# Network events
unifi_batch(tools=[
    {"tool": "unifi_list_events", "args": {"start": "<time>"}},
    {"tool": "unifi_list_alarms"}
])

# Camera events (if Protect available)
protect_batch(tools=[
    {"tool": "protect_list_events", "args": {"start": "<time>"}},
    {"tool": "protect_list_smart_detections", "args": {"detection_type": "person", "start": "<time>"}}
])

# Door events (if Access available)
access_batch(tools=[
    {"tool": "access_list_events", "args": {"start": "<time>"}},
    {"tool": "access_recent_events"}
])
```

### Step 2: Correlate by timestamp
- Match person detections (Protect) with door access events (Access)
- Match new network clients (Network) with access grants
- Look for denied access attempts or alarm events

### Step 3: Deep dive
- `protect_get_event_thumbnail(event_id="...")` → visual evidence
- `protect_get_snapshot(camera_id="...", include_image=true)` → current camera view
- `access_get_event(event_id="...")` → who was involved
- `unifi_get_client_details(mac="...")` → device details

---

## Device Connectivity Troubleshooting

**Scenario:** A camera or access reader appears offline in its application. Determine if it's a network issue or application issue.

### Camera Offline
1. `protect_get_camera(camera_id="...")` → get camera IP and MAC, check connection state
2. `unifi_lookup_by_ip(ip="<camera IP>")` → is it on the network?
3. If not found by IP: `unifi_list_clients` → search by MAC
4. `unifi_get_device_details(mac="<switch MAC>")` → check the switch port the camera connects to
5. If network looks fine: `protect_reboot_camera(camera_id="...", confirm=true)` → application-level restart

### Access Reader Offline
1. `access_get_device(device_id="...")` → get reader IP and MAC, check connection state
2. `unifi_lookup_by_ip(ip="<reader IP>")` → network-level status
3. Check the hub: `access_list_devices` → find the hub this reader connects to
4. If network connectivity confirmed: `access_reboot_device(device_id="...", confirm=true)` → reboot reader

### General Pattern
The investigation flows from application layer → network layer:
1. Get device details from the application server (Protect or Access) to find IP/MAC
2. Cross-reference with Network server to check connectivity
3. If network is fine, the issue is application-level → try rebooting via the application
4. If network shows the device disconnected, troubleshoot the network (switch, cable, PoE)

---

## Full Site Health Check

**Scenario:** Quick overall health assessment of the entire UniFi deployment.

### Batch across all servers
```
# Network health
unifi_batch(tools=[
    {"tool": "unifi_get_system_info"},
    {"tool": "unifi_get_network_health"},
    {"tool": "unifi_list_devices"},
    {"tool": "unifi_get_alerts"}
])

# Protect health (if available)
protect_batch(tools=[
    {"tool": "protect_get_system_info"},
    {"tool": "protect_get_health"},
    {"tool": "protect_get_firmware_status"},
    {"tool": "protect_get_recording_status"}
])

# Access health (if available)
access_batch(tools=[
    {"tool": "access_get_system_info"},
    {"tool": "access_get_health"},
    {"tool": "access_list_devices"},
    {"tool": "access_list_doors"}
])
```

### What to check in results
- **Network:** Any devices in error/disconnected state? Active alarms? ISP issues?
- **Protect:** NVR storage getting full? CPU/memory pressure? Cameras not recording? Firmware updates available?
- **Access:** Auth paths healthy? Any devices offline? Doors in unexpected state?

---

## New Employee Onboarding

**Scenario:** Set up network and physical access for a new team member.

### Network Setup
1. Check available networks: `unifi_list_networks`
2. If needed, create a user group with bandwidth profile: `unifi_create_usergroup(...)`
3. Create guest vouchers if needed: `unifi_create_voucher(...)`

### Physical Access (requires Access server)
1. `access_list_policies` → find the right access policy for their role
2. `access_create_credential(credential_type="nfc", credential_data={"user_id": "...", "token": "..."})` → issue NFC card
3. Or: `access_create_credential(credential_type="pin", credential_data={"user_id": "...", "pin_code": "..."})` → issue PIN

### Camera Coverage (requires Protect server)
1. `protect_list_cameras` → verify cameras cover the areas they'll access
2. `protect_get_recording_status` → confirm those cameras are recording

---

## Visitor Management (End-to-End)

**Scenario:** Prepare for a visitor including network access, door access, and camera awareness.

### Before Visit
1. Create visitor pass: `access_create_visitor(name="...", access_start="...", access_end="...", email="...")`
2. Create WiFi voucher: `unifi_create_voucher(...)` → give them temporary internet access
3. Check camera coverage of entry areas: `protect_list_cameras` → ensure front door cameras are operational

### During Visit
1. Monitor entry: `access_recent_events` → see when they arrive
2. If needed: `access_unlock_door(door_id="...", confirm=true)` → remote unlock for specific doors

### After Visit
1. Verify pass expired: `access_get_visitor(visitor_id="...")` → check status
2. Review footage if needed: `protect_list_events(camera_id="<lobby cam>", start="<visit start>", end="<visit end>")`

---

## After-Hours Activity Audit

**Scenario:** Review all activity outside business hours for security compliance.

### Gather data (batch within each server)
```
# Network: who was connected after hours?
unifi_list_events(start="<close time>", end="<open time>")

# Protect: any person detections after hours?
protect_list_smart_detections(
    detection_type="person",
    start="<close time>",
    end="<open time>"
)

# Access: who badged in after hours?
access_list_events(start="<close time>", end="<open time>")
access_get_activity_summary(days=1)
```

### Cross-reference
- Match person detections (Protect) with access events (Access)
- Person detected but no access event → possible unauthorized entry
- Access event but no person detected → credential-only entry (e.g., from inside)
- Network clients connecting after hours → remote access or forgotten devices

---

## Emergency Lockdown

**Scenario:** Lock all doors and assess the situation.

### Step 1: Lock all doors immediately
1. `access_list_doors` → get all door IDs
2. Lock each door (batch for speed):
```
access_batch(tools=[
    {"tool": "access_lock_door", "args": {"door_id": "...", "confirm": true}},
    {"tool": "access_lock_door", "args": {"door_id": "...", "confirm": true}}
    // ... repeat for each door
])
```

### Step 2: Assess via cameras
1. `protect_list_cameras` → check all camera states
2. `protect_recent_events` → any recent smart detections
3. Get snapshots from key cameras:
```
protect_batch(tools=[
    {"tool": "protect_get_snapshot", "args": {"camera_id": "<lobby>", "include_image": true}},
    {"tool": "protect_get_snapshot", "args": {"camera_id": "<entrance>", "include_image": true}}
])
```

### Step 3: Monitor network for anomalies
1. `unifi_list_clients` → any unexpected devices?
2. `unifi_get_alerts` → any network alarms?

---

## Device Inventory Across Systems

**Scenario:** Get a complete picture of all hardware in the deployment.

### Gather from all servers
```
# Network infrastructure
unifi_list_devices  → APs, switches, gateways

# Cameras and peripherals
protect_batch(tools=[
    {"tool": "protect_list_cameras"},
    {"tool": "protect_list_lights"},
    {"tool": "protect_list_sensors"},
    {"tool": "protect_list_chimes"}
])

# Access hardware
access_list_devices  → hubs, readers, relays, intercoms
```

### Cross-reference
- Protect cameras and Access readers also appear as clients in Network
- Use Network tools to check firmware, IP assignments, PoE status for those devices
- `unifi_get_device_details` on the switch port can reveal PoE power draw per device
