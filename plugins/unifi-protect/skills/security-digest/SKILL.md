---
name: security-digest
description: Generate a security digest summarizing events across UniFi Protect cameras, Access door events, and Network firewall activity. Use when asked about what happened overnight, security summary, event digest, recent activity, or reviewing camera and access events.
---

# Security Digest

You are generating a security digest that summarizes events across multiple UniFi systems. This skill
can operate in two modes depending on whether the event collector daemon is running:

- **Rich mode** — collector has been running and events are buffered in SQLite; full history, correlation, and counting available
- **Fallback mode** — no collector; queries MCP tools directly; limited to API retention windows

## Setup Check

Before generating a digest, verify the primary server is reachable:

- `UNIFI_PROTECT_HOST` must be set — this is the required variable for the Protect MCP server
- Confirm connectivity: call `protect_tool_index` to verify the Protect server is available

For full cross-product correlation (CORR-01 through CORR-05), the unifi-network and unifi-access
plugins must also be configured. Check availability by calling `unifi_tool_index` and
`access_tool_index`. Correlation rules that span missing servers are automatically skipped —
the digest degrades gracefully to single-source output.

## Starting the Event Collector (optional, recommended)

For rich historical digests that cover hours or days of activity, start the event collector daemon
before the period you want to review. The collector polls the MCP servers on a configurable interval
and stores all events in a local SQLite database (`events.db`).

**Start the collector:**

```bash
bash scripts/start-collector.sh
```

Optional flags:
- `--poll-interval N` — polling interval in seconds (default: 10)
- `--servers protect,network` — which servers to poll (default: protect,network)
- `--timeout N` — auto-stop after N seconds (default: 1800, i.e. 30 minutes)
- `--state-dir DIR` — where to write `events.db` and the PID file (default: `.claude/unifi-skills`)

The script outputs JSON confirming the daemon is running and the PID. Events accumulate in SQLite
for as long as the daemon runs — this is what enables overnight digests covering 8–12 hours of
activity rather than just the last few minutes the API retains.

**Stop the collector when done:**

```bash
bash scripts/stop-collector.sh
```

The collector is optional. If it is not running, `generate-digest.py` falls back to querying the
MCP tools directly. The fallback still produces a valid digest but is limited to whatever the
UniFi API currently holds in its event buffer (typically the last 1–2 hours).

## Generating a Digest

Run `scripts/generate-digest.py` to produce the digest:

```bash
python scripts/generate-digest.py --range overnight
```

**How the script selects its data source:**

- If `events.db` exists and has data buffered within the last 60 minutes → **rich mode** (reads from SQLite)
- Otherwise → **fallback mode** (queries MCP tools directly for the requested time range)

**Time range options (`--range`):**

| Range | Window | Typical use |
|-------|--------|-------------|
| `overnight` | Last 12 hours (6 pm–6 am) | Morning review after the night |
| `today` | Since midnight | End-of-day summary |
| `recent` | Last 4 hours | Quick check during the day |
| `24h` | Full 24 hours | Daily security report |

**Output format (`--format`):**

- `--format json` (default) — structured JSON suitable for further processing or display
- `--format human` — Markdown-formatted text for immediate reading

**Additional options:**

- `--state-dir DIR` — override state directory (also read from `UNIFI_SKILLS_STATE_DIR` env var)
- `--mcp-url URL` — override MCP server URL for fallback mode

**Example — rich overnight digest in human format:**

```bash
python scripts/generate-digest.py --range overnight --format human
```

**Output structure (JSON mode):**

```json
{
  "success": true,
  "mode": "collector",
  "status": "alert|notable|clear",
  "summary": "...",
  "notable_events": [...],
  "correlations": [...],
  "activity_counts": { "protect": {...}, "access": {...}, "network": {...} },
  "recommendations": [...],
  "time_range": { "name": "overnight", "start": "...", "end": "..." }
}
```

## Understanding Results

The digest script classifies events using three reference models. Consult these files for the
full classification logic:

- `references/event-types.md` — catalog of all event type codes from Protect, Access, and Network, with key fields and digest relevance
- `references/severity-model.md` — how base severity is computed and modified by time of day, location, and event frequency; includes the full classification matrix
- `references/correlation-rules.md` — the five deterministic cross-product rules with their logic, time windows, and recommended responses

**Status values in the output:**

- `clear` — no notable events; nothing requires attention
- `notable` — medium-severity events present; worth reviewing
- `alert` — one or more high-severity events or fired correlations; prompt review warranted

Lead with "nothing to worry about" when status is `clear`. Do not invent concerns for quiet periods.

## Cross-Product Correlation

When events from multiple MCP servers are available (Protect + Access + Network), the digest runs
five deterministic correlation rules. These rules identify security-relevant combinations that
neither data source would surface alone:

| Rule | Sources | Window | Severity | Pattern |
|------|---------|--------|----------|---------|
| CORR-01 | Protect + Access | 2 min | High | Motion at an entry camera with no corresponding badge-in |
| CORR-02 | Network + Protect | 5 min | Medium | New/unknown device on the network near a person detection |
| CORR-03 | Access + Protect | 3 min | High | Access denied at a door followed by continued motion |
| CORR-04 | Network + Protect | 5 min | High | Network device offline coinciding with camera disconnections |
| CORR-05 | Access + Protect | 5 min | Low | After-hours badge-in with no approach motion before it (audit trail) |

When multiple rules fire on the same events, the highest severity wins and the rules are listed
together in a single merged incident. See `references/correlation-rules.md` for full logic,
pseudocode, and recommended responses for each rule.

## Manual Procedure (fallback)

If the scripts are unavailable (e.g., running inside a restricted MCP client that cannot execute
bash or Python), use this tool-call-based procedure directly.

### Step 1: Determine Time Range

Default ranges if the user does not specify:
- "overnight" = last 12 hours (6 pm to 6 am)
- "today" = since midnight
- "recent" = last 4 hours

### Step 2: Gather Events (parallel where possible)

**From Protect** (if available):
- `protect_list_events` with time range filter
- `protect_list_smart_detections` with time range
- `protect_recent_events` for very recent events

**From Access** (if available):
- `access_list_events` with time range filter
- `access_recent_events`
- `access_get_activity_summary`

**From Network** (if available):
- `unifi_list_alarms`
- `unifi_list_events` with time range
- `unifi_get_dpi_stats`

### Step 3: Analyze and Correlate

Apply severity from `references/severity-model.md`. Apply correlation rules from
`references/correlation-rules.md`. Prioritize smart detection events (person, vehicle, package)
as the highest-signal items.

### Step 4: Report

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

- Start the collector at the beginning of the period you want to analyze (e.g., before leaving for
  the night) for the richest overnight digests. The longer the collector runs, the more history it accumulates.
- Use `--format human` for a quick readable review; use `--format json` when passing results to
  another tool or workflow.
- The most security value comes from overnight and 24h ranges where time-of-day severity modifiers
  elevate routine events to notable ones.
- If only one MCP server is available, produce a single-source digest — do not apologize for
  missing data, just work with what is connected.
- Use `protect_get_event_thumbnail` to offer visual evidence for notable person or vehicle
  detections when the user wants to see what triggered an alert.
- If status is `clear`, lead with that — do not manufacture concerns for quiet periods.
