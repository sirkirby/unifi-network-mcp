---
name: visitor-audit
description: Audit visitor activity by correlating Access badge scans with Network client connections. Use when the user wants to know who visited, when, and what devices they brought.
---

# Visitor Audit

You are auditing visitor activity by correlating physical access with network presence.

## What You Do

Given a time window (e.g., "today", "this week"), you:

1. Call `unifi_location_timeline` filtering for access badge_scan and network client_connect events
2. Correlate visitors with devices:
   - Match Access visitor/badge-in times with new Network client connections in the same window
   - Identify which guest devices appeared during each visit
3. Present a visitor log: who came, when, how long, and what devices they connected

## Requirements

- Access server must be connected (primary data source for visitor logs)
- Network server adds device correlation (which devices appeared during visits)

## Example Prompts

- "Who visited today and what devices did they bring?"
- "Visitor audit for this week — any unusual guest device activity?"
- "Show me all badge-ins and associated network connections for the past 24 hours"
