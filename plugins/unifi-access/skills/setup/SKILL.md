---
name: setup
description: Configure the UniFi Access MCP server — set controller host, credentials, and permissions
allowed-tools: Read, Bash, AskUserQuestion
---

# Set Up UniFi Access MCP Server

Walk the user through configuring their UniFi Access controller connection. **Ask each question one at a time using AskUserQuestion. Wait for the answer before proceeding.**

## Step 1: Controller Host

Ask: "What is your UniFi controller's IP address or hostname?" (e.g., 192.168.1.1)

If the user already has Network or Protect configured (check `.claude/settings.json` for existing `UNIFI_*` env vars), ask: "Is Access on the same controller?" If yes, use the same host.

## Step 2: Authentication

Access uses dual authentication — explain this to the user:

"UniFi Access has two auth paths:
- **API key** (port 12445) — for read-only operations (listing doors, events, devices)
- **Username + password** (port 443) — required for mutations (lock/unlock, credentials, visitors)

You can configure one or both."

Ask: "Which auth paths do you want to set up?"

Options:
- "API key only" — read-only access to Access data
- "Username and password only" — full access including mutations
- "Both" — recommended for full flexibility

## Step 3: Collect Credentials

Based on their choice, ask for API key and/or username+password (one question at a time).

## Step 4: Permission Configuration

Ask: "Do you want to enable any write permissions? By default, ALL mutations are disabled for Access (door lock/unlock, credentials, visitors)."

Options:
- "Read-only for now" — can view doors, events, users but not control anything
- "Enable door control" — lock/unlock doors
- "Enable credential management" — create/revoke NFC, PIN, mobile credentials
- "Enable visitor management" — create/delete visitor passes
- "Enable all" — door control + credentials + visitors + device reboot
- "Custom" — ask which categories to enable

## Step 5: Write Configuration

Use the `set-env.sh` script to write all collected values to `.claude/settings.json`. The script handles creating the file, merging into existing env vars, and masking sensitive values in output.

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/set-env.sh \
  UNIFI_ACCESS_HOST=<host> \
  UNIFI_ACCESS_API_KEY=<api-key> \
  UNIFI_ACCESS_USERNAME=<username> \
  UNIFI_ACCESS_PASSWORD=<password>
```

If the host and credentials are the same as existing shared `UNIFI_*` vars, use the shared prefix instead to avoid duplication.

If permissions were enabled, also pass those:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/set-env.sh \
  UNIFI_PERMISSIONS_DOORS_UPDATE=true \
  UNIFI_PERMISSIONS_CREDENTIALS_CREATE=true \
  UNIFI_PERMISSIONS_VISITORS_CREATE=true
```

Permission variables by option:
- **Door control:** `UNIFI_PERMISSIONS_DOORS_UPDATE=true`
- **Credential management:** `UNIFI_PERMISSIONS_CREDENTIALS_CREATE=true`, `UNIFI_PERMISSIONS_CREDENTIALS_DELETE=true`
- **Visitor management:** `UNIFI_PERMISSIONS_VISITORS_CREATE=true`, `UNIFI_PERMISSIONS_VISITORS_DELETE=true`
- **Enable all:** all of the above + `UNIFI_PERMISSIONS_DEVICES_UPDATE=true`, `UNIFI_PERMISSIONS_POLICIES_UPDATE=true`

## Step 6: Verify and Restart

Tell the user:

"Configuration saved to `.claude/settings.json`. Restart Claude Code to connect the MCP server. After restart, run `/mcp` to verify the connection, or just ask me about your doors."

Show a summary table of what was configured, noting which auth paths are active and what permissions are enabled.
