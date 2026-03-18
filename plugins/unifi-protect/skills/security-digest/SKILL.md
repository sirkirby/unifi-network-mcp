---
name: security-digest
description: Generate a security digest summarizing events across UniFi Protect cameras, Access door events, and Network firewall activity. Use when asked about what happened overnight, security summary, event digest, recent activity, or reviewing camera and access events.
---

# Security Digest

You are generating a security digest that summarizes events across multiple UniFi systems. Your goal is to surface the most important security-relevant events in a clear, concise report.

## Required MCP Servers

This skill works best with multiple MCP servers. Check which are available:
- **unifi-protect** (primary) — camera events, smart detections, motion
- **unifi-access** (optional) — door events, badge-ins, visitor passes
- **unifi-network** (optional) — firewall blocks, alarms, client events

Use each server's tool index meta-tool to verify available tools: `protect_tool_index`, `access_tool_index`, `unifi_tool_index`. Adapt the digest based on which servers are connected — if a tool index call fails, that server is not available.

## Digest Procedure

### Step 1: Determine Time Range

If the user specifies a range, use it. Otherwise, default to:
- "overnight" = last 12 hours (6pm to 6am)
- "today" = since midnight
- "recent" = last 4 hours

### Step 2: Gather Events (parallel where possible)

**From Protect** (if available):
- `protect_list_events` with time range filter — all events
- `protect_list_smart_detections` with time range — person, vehicle, animal, package detections
- `protect_recent_events` — fast buffer check for very recent events

**From Access** (if available):
- `access_list_events` with time range filter — door opens, badge-ins, denials
- `access_recent_events` — fast buffer check
- `access_get_activity_summary` — aggregated activity counts

**From Network** (if available):
- `unifi_list_alarms` — active security alerts
- `unifi_list_events` with time range — client connects/disconnects, device state changes
- `unifi_get_dpi_stats` — traffic pattern summary

### Step 3: Analyze and Correlate

**Protect events — categorize by severity:**
- **High:** Person detected at unusual hours, unknown vehicle, door/window sensor triggered
- **Medium:** Package delivery, frequent motion in typically quiet areas
- **Low:** Animal detection, routine motion during business hours

**Access events — flag anomalies:**
- Access denied events (failed badge attempts)
- Door held open / forced open alerts
- Access outside of scheduled hours
- Visitor passes used outside valid windows

**Network events — security relevant only:**
- Blocked traffic from internal devices to external IPs (potential compromise)
- New/unknown devices joining the network
- Alarms (rogue AP, connectivity issues)

**Cross-product correlation (if multiple servers available):**
- Motion at a door with no corresponding badge-in → potential unauthorized access
- New device on network + motion detection → potential intruder with device
- Access denied + motion continuing → someone trying to get in

### Step 4: Report

Present findings in this format:

```
## Security Digest — [date/time range]

### Summary
[1-2 sentence overview: "Quiet night with one notable event" or "Multiple security-relevant events detected"]

### Notable Events
[Only events worth human attention, in chronological order]

**[Time] — [Event description]**
- Source: [Protect/Access/Network]
- Details: [What happened]
- Severity: [High/Medium/Low]
- [Cross-product correlation if applicable]

### Activity Counts
| Source | Events | Notable |
|--------|--------|---------|
| Protect (cameras) | [count] | [person/vehicle/package counts] |
| Access (doors) | [count] | [denied/after-hours counts] |
| Network | [count] | [alarm/blocked counts] |

### Recommendations
[Only if action is warranted — e.g., "Review camera footage at [time]" or "Investigate blocked traffic from NAS"]
```

## Tips
- Lead with "nothing to worry about" if the digest is clean — don't invent concerns.
- For overnight digests, focus on events during non-business hours (typically 10pm-6am).
- If only one MCP server is available, produce a single-source digest — don't apologize for missing data, just work with what you have.
- Smart detection events (person, vehicle, package) from Protect are the highest-signal items. Prioritize these.
- Use `protect_get_event_thumbnail` to offer visual evidence for notable events if the user wants to see what happened.
