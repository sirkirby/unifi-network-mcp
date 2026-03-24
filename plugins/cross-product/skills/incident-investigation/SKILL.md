---
name: incident-investigation
description: Investigate a network incident by correlating device events with camera footage and physical access logs. Use when the user reports a device going offline, a network anomaly, or wants to understand what caused an infrastructure event.
---

# Network Incident Investigation

You are investigating a network infrastructure event using cross-product correlation.

## What You Do

Given an incident (e.g., "switch went offline", "AP stopped responding"), you:

1. Get the device event details from Network (device name, time, status change)
2. Call `unifi_location_timeline` with the time window around the incident
3. Look for correlated events:
   - Camera footage near the device location at the time of the incident
   - Physical access events (was someone in the area?)
   - Other devices on the same network segment affected?
4. Present a timeline of what happened with your assessment

## Requirements

- Network server must be connected (this is the primary data source)
- Protect server adds camera correlation (optional but valuable)
- Access server adds physical access context (optional)

## Example Prompts

- "A switch went offline at 2 AM — what happened?"
- "The guest WiFi AP has been dropping — investigate"
- "We lost connectivity to the warehouse at 3:15 PM, what do you see?"
