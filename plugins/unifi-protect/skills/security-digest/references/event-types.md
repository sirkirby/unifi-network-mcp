# Event Type Catalog

Cross-product reference for all event types surfaced by the security digest skill.
Events are sourced from three MCP servers: UniFi Protect, UniFi Access, and UniFi Network.

---

## UniFi Protect Events

**Source server:** `unifi-protect-mcp`
**Primary tools:** `protect_list_events`, `protect_list_smart_detections`

### Motion Detection

| Type Code | Description | Tool | Digest Relevance |
|-----------|-------------|------|-----------------|
| `motion` | Generic motion detected in camera zone | `protect_list_events` | Baseline activity signal; combined with Access and Network events for correlation |
| `smartDetectZone` | Motion within a user-defined smart zone | `protect_list_events` | Higher-fidelity than raw motion; zone name indicates location context |

**Key fields:** `camera_id`, `start`, `end`, `thumbnail_id`, `score`

### Smart Detections

| Type Code | Description | Tool | Digest Relevance |
|-----------|-------------|------|-----------------|
| `person` | Person detected by AI model | `protect_list_smart_detections` | Primary human-presence signal; severity depends on time and location |
| `vehicle` | Vehicle detected (car, truck, motorcycle) | `protect_list_smart_detections` | Perimeter and parking-area monitoring |
| `animal` | Animal detected (pet, wildlife) | `protect_list_smart_detections` | Generally informational; can reduce false positives on motion-only alerts |
| `package` | Package left at entrance | `protect_list_smart_detections` | Delivery tracking; low severity baseline |
| `licenseplate` | Vehicle license plate recognized | `protect_list_smart_detections` | Used for vehicle identification when plate-reading cameras are present |

**Key fields:** `camera_id`, `type`, `score` (0.0–1.0 confidence), `start`, `end`, `thumbnail_id`, `zones`

**Confidence score guidance:**
- `>= 0.90`: High confidence — treat as confirmed detection
- `0.70–0.89`: Medium confidence — include in digest with caveat
- `< 0.70`: Low confidence — suppress from digest or aggregate as noise

### Doorbell Events

| Type Code | Description | Tool | Digest Relevance |
|-----------|-------------|------|-----------------|
| `ring` | Doorbell button pressed | `protect_list_events` | Visitor intent signal; combined with person detection confirms visitor |

**Key fields:** `camera_id`, `start`, `thumbnail_id`

### Sensor Events

| Type Code | Description | Tool | Digest Relevance |
|-----------|-------------|------|-----------------|
| `sensorClosed` | Door or window sensor closed | `protect_list_events` | Entry/exit signal from physical sensors |
| `sensorOpened` | Door or window sensor opened | `protect_list_events` | Entry/exit signal; correlate with Access badge events |
| `sensorAlarm` | Sensor alarm triggered (motion, tamper, leak) | `protect_list_events` | Elevated severity; include in digest regardless of time |

**Key fields:** `camera_id` (sensor device uses camera_id field), `start`, `type`

---

## UniFi Access Events

**Source server:** `unifi-access-mcp` (or the network server's access endpoints)
**Primary tool:** `access_list_events`

### Successful Access

| Type Code | Description | Tool | Digest Relevance |
|-----------|-------------|------|-----------------|
| `ACCESS_GRANT` | Badge-in accepted, door unlocked | `access_list_events` | Normal operation; after-hours grants are elevated to Medium or Low |
| `VISITOR_GRANT` | Visitor pass accepted | `access_list_events` | Temporary credential use; log with visitor name if available |
| `REMOTE_UNLOCK` | Door unlocked via app or admin | `access_list_events` | Remote action; include when outside business hours |

**Key fields:** `door_id`, `door_name`, `user_id`, `user_display_name`, `credential_type`, `timestamp`

### Denied Access

| Type Code | Description | Tool | Digest Relevance |
|-----------|-------------|------|-----------------|
| `ACCESS_DENY` | Badge rejected (invalid, revoked, or wrong door) | `access_list_events` | Single denial = Low; repeated denials = High (see CORR-03) |
| `CREDENTIAL_EXPIRED` | Credential presented but expired | `access_list_events` | Medium; may indicate an oversight rather than an attack |
| `SCHEDULE_DENY` | Valid credential but outside allowed hours | `access_list_events` | Low to Medium; repeated = suspicious |
| `ANTI_PASSBACK` | Credential used out of sequence (tailgating indicator) | `access_list_events` | Medium; review footage at the door |

**Key fields:** `door_id`, `door_name`, `user_id`, `user_display_name`, `deny_reason`, `timestamp`

### Door State Events

| Type Code | Description | Tool | Digest Relevance |
|-----------|-------------|------|-----------------|
| `DOOR_HELD_OPEN` | Door left open past the hold-open timeout | `access_list_events` | Medium; common during deliveries, escalate if after-hours |
| `DOOR_FORCED_OPEN` | Door opened without an access event (physical bypass) | `access_list_events` | High; always include in digest |
| `DOOR_AJAR` | Door not fully latched | `access_list_events` | Low to Medium depending on location and time |

**Key fields:** `door_id`, `door_name`, `duration_seconds` (for held-open), `timestamp`

---

## UniFi Network Events

**Source server:** `unifi-network-mcp`
**Primary tools:** `unifi_list_events`, `unifi_list_alarms`

### Device Events

| Type Code | Prefix | Description | Tool | Digest Relevance |
|-----------|--------|-------------|------|-----------------|
| `EVT_SW_Connected` | `EVT_SW_` | Switch connected to controller | `unifi_list_events` | Informational unless unexpected |
| `EVT_SW_Disconnected` | `EVT_SW_` | Switch disconnected | `unifi_list_events` | High if correlated with camera offline (CORR-04) |
| `EVT_AP_Connected` | `EVT_AP_` | Access point connected | `unifi_list_events` | Informational |
| `EVT_AP_Disconnected` | `EVT_AP_` | Access point disconnected | `unifi_list_events` | High if correlated with camera offline (CORR-04) |
| `EVT_GW_Connected` | `EVT_GW_` | Gateway connected | `unifi_list_events` | Informational |
| `EVT_GW_Disconnected` | `EVT_GW_` | Gateway disconnected | `unifi_list_events` | Critical; full network disruption |

**Key fields:** `key`, `msg`, `time`, `site_id`, `ap` (device MAC), `ap_name`

### Client Events

| Type Code | Prefix | Description | Tool | Digest Relevance |
|-----------|--------|-------------|------|-----------------|
| `EVT_WU_Connected` | `EVT_WU_` | Wireless client connected to SSID | `unifi_list_events` | New/unknown MACs are medium severity (see CORR-02) |
| `EVT_WU_Disconnected` | `EVT_WU_` | Wireless client disconnected | `unifi_list_events` | Generally informational |
| `EVT_WG_Connected` | `EVT_WG_` | Wired client connected | `unifi_list_events` | Physical port access; unknown MACs are higher severity |
| `EVT_WG_Disconnected` | `EVT_WG_` | Wired client disconnected | `unifi_list_events` | Informational |
| `EVT_LU_Connected` | `EVT_LU_` | Client reconnected (roamed) | `unifi_list_events` | Informational |

**Key fields:** `key`, `msg`, `time`, `client` (MAC address), `client_name`, `ssid`, `ap`, `ap_name`

### Security Alerts

| Type Code | Prefix | Description | Tool | Digest Relevance |
|-----------|--------|-------------|------|-----------------|
| `EVT_IPS_IpsAlert` | `EVT_IPS_` | Intrusion Prevention System alert | `unifi_list_events` | High; always include in digest |
| `EVT_IPS_IpsBlock` | `EVT_IPS_` | IPS blocked a threat | `unifi_list_events` | Medium (blocked = mitigated); log for pattern analysis |
| `EVT_AD_LoginFailed` | `EVT_AD_` | Controller login failure | `unifi_list_events` | Medium; repeated = High |

**Key fields:** `key`, `msg`, `time`, `src_ip`, `dest_ip`, `proto`, `signature`, `category`

### Admin Actions

| Type Code | Prefix | Description | Tool | Digest Relevance |
|-----------|--------|-------------|------|-----------------|
| `EVT_AD_Login` | `EVT_AD_` | Admin logged into controller | `unifi_list_events` | Low during business hours; Medium after-hours |
| `EVT_AD_Logout` | `EVT_AD_` | Admin logged out | `unifi_list_events` | Informational |
| `EVT_AD_APIKeyCreate` | `EVT_AD_` | API key created | `unifi_list_events` | Medium; log for audit trail |

**Key fields:** `key`, `msg`, `time`, `admin`, `ip`

### Alarms

Alarms are distinct from events: they represent persistent conditions requiring acknowledgment.

| Severity | Description | Tool | Digest Relevance |
|----------|-------------|------|-----------------|
| `critical` | Service-affecting failure (gateway down, ISP loss) | `unifi_list_alarms` | Always include; highest priority in digest |
| `high` | Significant degradation (AP offline, switch port down) | `unifi_list_alarms` | Include in digest |
| `medium` | Non-critical issue (high interference, client issues) | `unifi_list_alarms` | Include if correlated with other events |
| `low` | Advisory (firmware available, config drift) | `unifi_list_alarms` | Include only if accumulating |

**Key fields:** `key`, `msg`, `time`, `severity`, `subsystem`, `archived` (false = unresolved)

---

## Field Glossary

| Field | Servers | Description |
|-------|---------|-------------|
| `camera_id` | Protect | Unique identifier for the camera or sensor device |
| `thumbnail_id` | Protect | Reference to a still frame captured at event time |
| `score` | Protect | AI confidence (0.0–1.0) for smart detection types |
| `door_id` | Access | Unique identifier for the access-controlled door |
| `user_display_name` | Access | Human-readable name of the credential holder |
| `deny_reason` | Access | Machine-readable reason for access denial |
| `key` | Network | Event type code (e.g., `EVT_AP_Disconnected`) |
| `msg` | Network | Human-readable event description |
| `ap` | Network | MAC address of the access point involved |
| `client` | Network | MAC address of the client involved |
| `archived` | Network | `false` if the alarm is unresolved |
