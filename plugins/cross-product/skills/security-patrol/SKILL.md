---
name: security-patrol
description: Show everything that happened at a specific area across all UniFi products (Network, Protect, Access) in a given time window. Use when the user asks about activity at a door, entrance, room, or area.
---

# Security Patrol

You are investigating activity at a specific area across all connected UniFi products.

## What You Do

Given an area (e.g., "front entrance", "server room", "main door") and a time window, you:

1. Call `unifi_location_timeline` with the area_hint and time range
2. Interpret the unified timeline — look for patterns:
   - Motion without badge-in (someone present but didn't scan)
   - New devices appearing when someone arrives
   - Access denied followed by continued motion
   - Device/camera outages that coincide
3. Present a clear narrative: what happened, in what order, and what's notable

## Requirements

- At least 2 of the 3 UniFi products (Network, Protect, Access) must be connected
- Relay mode required for full cross-product timeline
- Works with single-product in local mode (limited to that product's events)

## Example Prompts

- "Show me everything that happened at the front entrance in the last hour"
- "What activity was there near the server room overnight?"
- "Security check on the loading dock since 6 PM"
