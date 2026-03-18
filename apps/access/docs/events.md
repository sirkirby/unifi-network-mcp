# Event Streaming

The Access server provides event monitoring through a combination of websocket buffering, MCP resources, and query tools.

## Architecture

```
UniFi Access Controller
    |
    v  WebSocket (event listener)
    |
EventManager (processes + serializes events)
    |
    v  Ring buffer (in-memory)
    |
EventBuffer (deque, configurable size + TTL)
    |
    +---> MCP Resources (access://events/stream, access://events/stream/summary)
    +---> access_recent_events tool (filtered buffer queries)
    +---> access_subscribe_events tool (subscription instructions)
```

### How Events Flow

1. **WebSocket connection** -- The server connects to the Access controller's websocket endpoint when `ACCESS_WEBSOCKET_ENABLED=true`. This streams events in real time: door opens, access grants, denials, alarms, etc.

2. **Event processing** -- The `EventManager` receives raw websocket messages, filters for relevant event types, and serializes them to plain dicts.

3. **Ring buffer** -- Processed events are stored in an `EventBuffer` (a `deque` with configurable max size and TTL). When the buffer is full, the oldest event is silently dropped.

4. **Client access** -- MCP clients read buffered events via resources or tools. No events are lost between polls as long as the buffer does not overflow.

### WebSocket and Auth Paths

The websocket event listener depends on the authentication path:

- **API key auth** (port 12445) -- WebSocket event streaming is supported when an API key is configured. This is the primary path for real-time events.
- **Proxy session only** (port 443) -- WebSocket may not be available in proxy-only mode. REST-based event tools (`access_list_events`, `access_get_activity_summary`) will still work.

If you need real-time events, ensure `UNIFI_ACCESS_API_KEY` is configured.

## MCP Resources

### `access://events/stream`

Returns the full contents of the event buffer as a JSON array (newest first). Each event includes:

- `type` -- Event type (door_open, door_close, access_granted, access_denied, door_alarm, etc.)
- `door_id` -- Source door ID (if applicable)
- `user_id` -- User who triggered the event (if applicable)
- `timestamp` -- Event timestamp
- `result` -- Outcome of the access attempt
- `_buffered_at` -- Unix timestamp when the event entered the buffer

### `access://events/stream/summary`

A lightweight summary of the buffer: total event count, breakdown by event type, and breakdown by door. Useful for deciding whether to fetch the full stream.

```json
{
  "total_events": 42,
  "by_type": {"access_granted": 30, "access_denied": 8, "door_open": 4},
  "by_door": {"door-id-1": 25, "door-id-2": 17},
  "buffer_size": 100
}
```

## Tools for Event Access

| Tool | Source | Best for |
|------|--------|----------|
| `access_recent_events` | Websocket buffer | Real-time monitoring with filters |
| `access_list_events` | REST API | Historical queries with time ranges |
| `access_get_activity_summary` | REST API | Aggregated trends and counts |
| `access_subscribe_events` | -- | Getting subscription instructions |

### access_recent_events vs access_list_events

- **`access_recent_events`** reads from the in-memory buffer. It is fast (no API call) but limited to events received since the server started, up to the buffer size. Supports filtering by event_type, door_id, and limit.

- **`access_list_events`** queries the Access controller's REST API. It can access the full event history. Supports filtering by time range, door, user, and result limit.

Use `access_recent_events` for near-real-time monitoring. Use `access_list_events` for historical analysis.

## Recommended Client Pattern

MCP push notifications are not yet available from background websocket callbacks due to a FastMCP limitation. The recommended approach is **polling**:

1. Call `access_subscribe_events` to get resource URIs and instructions
2. Poll `access://events/stream/summary` every 5-10 seconds to check for new events
3. When the summary shows new events, read `access://events/stream` for full details
4. Or use `access_recent_events` tool with filters for targeted queries

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ACCESS_EVENT_BUFFER_SIZE` | `100` | Maximum events in the ring buffer |
| `ACCESS_EVENT_BUFFER_TTL` | `300` | Seconds before buffered events are considered expired |
| `ACCESS_WEBSOCKET_ENABLED` | `true` | Enable/disable the websocket listener |

### Tuning the Buffer

- **High-traffic environments** (many doors, frequent access events): increase `ACCESS_EVENT_BUFFER_SIZE` to 500+ and decrease poll interval to 2-3 seconds
- **Low-traffic environments**: default values work well; poll every 10-30 seconds
- **Memory-constrained**: reduce `ACCESS_EVENT_BUFFER_SIZE`; each event is ~1-2 KB

### Disabling the WebSocket

Set `ACCESS_WEBSOCKET_ENABLED=false` to disable real-time streaming. REST-based tools (`access_list_events`, `access_get_activity_summary`) will still work. The buffer-based tools and resources will return empty results.
