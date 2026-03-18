---
name: setup
description: Configure the UniFi Protect MCP server — set NVR host, credentials, and permissions
allowed-tools: Read, Bash, AskUserQuestion
---

# Set Up UniFi Protect MCP Server

Walk the user through configuring their UniFi Protect NVR connection. **Ask each question one at a time using AskUserQuestion. Wait for the answer before proceeding.**

## Step 1: Controller Host

Ask: "What is your UniFi controller's IP address or hostname?" (e.g., 192.168.1.1)

If the user already has a Network server configured (check for `UNIFI_NETWORK_HOST` or `UNIFI_HOST` in `.claude/settings.json`), ask: "Is Protect on the same controller as your Network server?" If yes, use the same host.

## Step 2: Credentials

If the user already has Network credentials configured with the shared `UNIFI_` prefix, mention they can reuse those. Only set `UNIFI_PROTECT_` prefixed variables if the credentials differ from the shared ones.

Ask for:
1. Username (local admin account — **not** a Ubiquiti SSO account)
2. Password

Username and password are **required**. These must be local admin credentials on the UniFi controller.

### Optional: API Key

After collecting credentials, mention:

"UniFi also supports API keys, but API key auth is **experimental** — it's limited to read-only operations and a subset of tools. Ubiquiti is still expanding API key support. Would you also like to configure an API key?"

If yes, ask for the API key string and include it as `UNIFI_PROTECT_API_KEY` in the configuration. If no, skip it.

## Step 4: Permission Configuration

Ask: "Do you want to enable any write permissions? By default, ALL mutations are disabled for Protect (camera settings, recording control, PTZ, reboots)."

Options:
- "Read-only for now" — safest, can view everything but change nothing
- "Enable camera management" — camera settings, recording toggle, PTZ, reboot
- "Enable all device management" — cameras + lights + chimes
- "Custom" — ask which categories to enable

## Step 5: Write Configuration

Use the `set-env.sh` script to write all collected values to `.claude/settings.json`. The script handles creating the file, merging into existing env vars, and masking sensitive values in output.

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/set-env.sh \
  UNIFI_PROTECT_HOST=<host> \
  UNIFI_PROTECT_USERNAME=<username> \
  UNIFI_PROTECT_PASSWORD=<password>
```

If the host and credentials are the same as existing shared `UNIFI_*` vars, use the shared prefix instead:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/set-env.sh \
  UNIFI_HOST=<host> \
  UNIFI_USERNAME=<username> \
  UNIFI_PASSWORD=<password>
```

If permissions were enabled, also pass those:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/set-env.sh \
  UNIFI_PERMISSIONS_CAMERAS_UPDATE=true
```

Permission variables by option:
- **Camera management:** `UNIFI_PERMISSIONS_CAMERAS_UPDATE=true`
- **All device management:** `UNIFI_PERMISSIONS_CAMERAS_UPDATE=true`, `UNIFI_PERMISSIONS_LIGHTS_UPDATE=true`, `UNIFI_PERMISSIONS_CHIMES_UPDATE=true`

## Step 6: Verify and Restart

Tell the user:

"Configuration saved to `.claude/settings.json`. Restart Claude Code to connect the MCP server. After restart, run `/mcp` to verify the connection, or just ask me about your cameras."

Show a summary table of what was configured.
