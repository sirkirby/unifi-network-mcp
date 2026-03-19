---
name: security-digest
description: Generate a security digest summarizing events across UniFi Protect cameras, Access door events, and Network firewall activity. Use when asked about what happened overnight, security summary, event digest, recent activity, or reviewing camera and access events.
---

# Security Digest

## Setup Check

Before generating a digest, verify the primary server is reachable:

- `UNIFI_PROTECT_HOST` must be set — this is the required variable for the Protect MCP server.
- Confirm connectivity by calling `protect_tool_index` to verify the Protect server is available.

For full cross-product correlation (CORR-01 through CORR-05), the unifi-network and unifi-access plugins must also be configured. Check availability by calling `unifi_tool_index` and `access_tool_index`. Correlation rules that span missing servers are automatically skipped — the digest degrades gracefully to single-source output.

## Generating a Digest

### Determine the Time Range

Default ranges if the user does not specify:
- **overnight** — last 12 hours (6 pm to 6 am)
- **today** — since midnight
- **recent** — last 4 hours

### Gather Events (parallel batch calls per server)

Use each server's batch tool to gather events in parallel within that server. Do not call these tools one at a time.

**From Protect** (required):

Use `protect_list_smart_detections` as the primary source — these are the highest-signal events (person, vehicle, package, animal). Only add `protect_list_events` with `event_type=motion` if you need raw motion data beyond smart detections. Skip `protect_recent_events` for digests — it only contains the last few minutes of buffered events and adds little value for historical ranges.

```
protect_batch([
  { "tool": "protect_list_smart_detections", "args": { "start": "...", "limit": 50, "compact": true } },
  { "tool": "protect_list_events", "args": { "start": "...", "event_type": "ring", "limit": 20, "compact": true } }
])
```

Use `compact=true` on all event queries for digests — it strips thumbnail_id, category, sub_category, and is_favorite fields, reducing response size by ~40%.

Events now include `camera_name` alongside `camera_id` — no need to call `protect_list_cameras` separately to resolve names.

**From Access** (if available):

```
access_batch([
  { "tool": "access_list_events", "args": { ... time range ... } },
  { "tool": "access_recent_events" },
  { "tool": "access_get_activity_summary" }
])
```

**From Network** (if available):

```
unifi_batch([
  { "tool": "unifi_list_alarms" },
  { "tool": "unifi_list_events", "args": { ... time range ... } }
])
```

The three batch calls (Protect, Access, Network) can be issued concurrently — they target independent servers.

## Analyzing Events

Use these reference documents to classify and correlate the gathered events:

- `references/event-types.md` — catalog of all event type codes from Protect, Access, and Network, with key fields and digest relevance. Consult before labeling any event type.
- `references/correlation-rules.md` — the five deterministic cross-product correlation rules (CORR-01 through CORR-05) with their logic, time windows, and recommended responses. Apply these when data from multiple servers is available.
- `references/severity-model.md` — how base severity is computed and modified by time of day, location, and event frequency. Includes the full classification matrix. Apply this before assigning High/Medium/Low labels.

Smart detection events (person, vehicle, package) are the highest-signal items — prioritize these when reviewing Protect data.

**Status classification:**
- `clear` — no notable events; nothing requires attention. Lead with "nothing to worry about."
- `notable` — medium-severity events present; worth reviewing.
- `alert` — one or more high-severity events or fired correlations; prompt review warranted.

Do not invent concerns for quiet periods.

## Cross-Product Correlation

When events from multiple servers are available, apply the five deterministic rules from `references/correlation-rules.md`:

| Rule | Sources | Window | Severity | Pattern |
|------|---------|--------|----------|---------|
| CORR-01 | Protect + Access | 2 min | High | Motion at an entry camera with no corresponding badge-in |
| CORR-02 | Network + Protect | 5 min | Medium | New/unknown device on the network near a person detection |
| CORR-03 | Access + Protect | 3 min | High | Access denied at a door followed by continued motion |
| CORR-04 | Network + Protect | 5 min | High | Network device offline coinciding with camera disconnections |
| CORR-05 | Access + Protect | 5 min | Low | After-hours badge-in with no approach motion before it (audit trail) |

When multiple rules fire on the same events, the highest severity wins and the rules are listed together in a single merged incident. See `references/correlation-rules.md` for full logic and pseudocode.

## Report Format

```
## Security Digest — [date/time range]

### Summary
[1-2 sentence overview]

### Notable Events
[Chronological; only events worth human attention]

**[Time] — [Event description]**
- Source: [Protect/Access/Network]
- Severity: [High/Medium/Low]
- [Correlation rule if applicable]

### Activity Counts
| Source | Events | Notable |
|--------|--------|---------|
| Protect | [count] | person=[n] vehicle=[n] package=[n] |
| Access | [count] | denied=[n] |
| Network | [count] | alarms=[n] |

### Recommendations
[Only if action is warranted]
```

## Tips

- Use each server's batch tool for parallel data gathering within that server. The three server batches (Protect, Access, Network) can run concurrently.
- Smart detections (person, vehicle, package) are the highest-signal events — surface these first when summarizing.
- If only one MCP server is available, produce a single-source digest. Do not apologize for missing data — work with what is connected.
- Use `protect_get_event_thumbnail` to offer visual evidence for notable person or vehicle detections when the user wants to see what triggered an alert.
- The most security value comes from overnight and 24h ranges where time-of-day severity modifiers (from `references/severity-model.md`) elevate routine events to notable ones.
- If status is `clear`, lead with that — do not manufacture concerns for quiet periods.
