---
name: setup
description: Configure the UniFi Network MCP server — set controller host, credentials, and permissions
allowed-tools: Read, Bash, AskUserQuestion
---

# Set Up UniFi Network MCP Server

Walk the user through configuring their UniFi Network controller connection. **Ask each question one at a time using AskUserQuestion. Wait for the answer before proceeding.**

## Step 1: Controller Host

Ask: "What is your UniFi controller's IP address or hostname?" (e.g., 192.168.1.1)

## Step 2: Credentials

Ask for:
1. Username (local admin account — **not** a Ubiquiti SSO account)
2. Password

Username and password are **required**. These must be local admin credentials on the UniFi controller.

### Optional: API Key

After collecting credentials, mention:

"UniFi also supports API keys, but API key auth is **experimental** — it's limited to read-only operations and a subset of tools. Ubiquiti is still expanding API key support. Would you also like to configure an API key?"

If yes, ask for the API key string and include it as `UNIFI_NETWORK_API_KEY` in the configuration. If no, skip it.

## Step 4: Optional Settings

Ask: "Any additional settings to configure?"

Options:
- "Use defaults" — port 443, site 'default', SSL verification off, lazy tool loading
- "Customize" — ask about each: port, site name, SSL verification, tool registration mode

## Step 5: Permission Configuration

Ask: "Do you want to enable any write permissions? By default, the server is read-only for high-risk categories."

Options:
- "Read-only for now" — skip, can be configured later
- "Enable common write permissions" — enable firewall, port forwards, QoS, traffic routes, VPN clients
- "Enable all write permissions" — enable everything except delete operations
- "Custom" — ask which categories to enable

## Step 6: Write Configuration

Use the `set-env.sh` script to write all collected values to `.claude/settings.json`. The script handles creating the file, merging into existing env vars, and masking sensitive values in output.

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/set-env.sh \
  UNIFI_NETWORK_HOST=<host> \
  UNIFI_NETWORK_USERNAME=<username> \
  UNIFI_NETWORK_PASSWORD=<password>
```

Only pass variables the user provided values for. Use the `UNIFI_NETWORK_` prefix so it doesn't conflict with other server plugins.

If permissions were enabled, also pass those:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/set-env.sh \
  UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE=true \
  UNIFI_PERMISSIONS_FIREWALL_POLICIES_UPDATE=true \
  UNIFI_PERMISSIONS_PORT_FORWARDS_CREATE=true \
  UNIFI_PERMISSIONS_PORT_FORWARDS_UPDATE=true
```

Common permission variables for "enable all write":
- `UNIFI_PERMISSIONS_NETWORKS_CREATE=true`, `UNIFI_PERMISSIONS_NETWORKS_UPDATE=true`
- `UNIFI_PERMISSIONS_WLANS_CREATE=true`, `UNIFI_PERMISSIONS_WLANS_UPDATE=true`
- `UNIFI_PERMISSIONS_DEVICES_UPDATE=true`
- `UNIFI_PERMISSIONS_CLIENTS_UPDATE=true`
- `UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE=true`, `UNIFI_PERMISSIONS_FIREWALL_POLICIES_UPDATE=true`
- `UNIFI_PERMISSIONS_PORT_FORWARDS_CREATE=true`, `UNIFI_PERMISSIONS_PORT_FORWARDS_UPDATE=true`
- `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_UPDATE=true`
- `UNIFI_PERMISSIONS_QOS_RULES_CREATE=true`, `UNIFI_PERMISSIONS_QOS_RULES_UPDATE=true`
- `UNIFI_PERMISSIONS_VPN_CLIENTS_UPDATE=true`
- `UNIFI_PERMISSIONS_ROUTES_CREATE=true`, `UNIFI_PERMISSIONS_ROUTES_UPDATE=true`

## Step 7: Verify and Restart

Tell the user:

"Configuration saved to `.claude/settings.json`. Restart Claude Code to connect the MCP server. After restart, run `/mcp` to verify the connection, or just ask me about your network."

Show a summary table of what was configured.
