# Permission System

Permissions control which mutating tools are available. High-risk operations are disabled by default; read-only tools are always available.

## How It Works

1. Each mutating tool declares a **category** and **action** (create, update, or delete)
2. At startup, the server checks permission config for that category/action
3. Denied tools are **not registered** with the MCP server — they cannot be called
4. All tools remain discoverable via `unifi_tool_index` regardless of permission status

## Priority Order

1. **Environment variables** (highest) — `UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>=true`
2. **Config YAML** — `permissions.<category>.<action>` in `config.yaml`
3. **Default section** — `permissions.default.<action>` in `config.yaml`
4. **Hardcoded fallback** — `read: true`, `delete: false`

## Category Defaults

### Disabled by Default (High Risk)

| Category | Create | Update | Delete | Rationale |
|----------|--------|--------|--------|-----------|
| `networks` | no | no | no | Can cause network outages |
| `wlans` | no | no | no | Can disconnect all Wi-Fi clients |
| `devices` | no | no | no | Firmware upgrades cause downtime |
| `clients` | no | no | no | Affects user connectivity |
| `routes` | no | no | no | Can disrupt routing |
| `vpn_servers` | no | — | no | Create/delete restricted; update allowed |

### Enabled by Default (Lower Risk)

| Category | Create | Update | Delete |
|----------|--------|--------|--------|
| `firewall_policies` | yes | yes | no |
| `traffic_routes` | yes | yes | no |
| `port_forwards` | yes | yes | no |
| `qos_rules` | yes | yes | no |
| `vpn_clients` | yes | yes | no |
| `acl_rules` | yes | yes | no |
| `vouchers` | yes | yes | no |
| `usergroups` | yes | yes | no |

**Note:** Delete is denied by default across all categories and requires explicit opt-in.

## Enabling Permissions

### Environment Variables (Recommended)

```bash
# Enable network creation
export UNIFI_PERMISSIONS_NETWORKS_CREATE=true

# Enable device management
export UNIFI_PERMISSIONS_DEVICES_UPDATE=true

# Enable delete for ACL rules
export UNIFI_PERMISSIONS_ACL_RULES_DELETE=true
```

For Claude Desktop, add to the `env` section:
```json
{
  "env": {
    "UNIFI_PERMISSIONS_NETWORKS_CREATE": "true",
    "UNIFI_PERMISSIONS_DEVICES_UPDATE": "true"
  }
}
```

For Docker:
```bash
docker run -e UNIFI_PERMISSIONS_NETWORKS_CREATE=true ...
```

Accepted values: `true`, `1`, `yes`, `on` (case-insensitive).

### Config File

Edit `src/unifi_network_mcp/config/config.yaml`:

```yaml
permissions:
  networks:
    create: true
    update: true
```

Then restart the server. No manifest rebuild is needed for permission changes.

## All Permission Variables

| Category | Create | Update | Delete |
|----------|--------|--------|--------|
| networks | `UNIFI_PERMISSIONS_NETWORKS_CREATE` | `UNIFI_PERMISSIONS_NETWORKS_UPDATE` | `UNIFI_PERMISSIONS_NETWORKS_DELETE` |
| wlans | `UNIFI_PERMISSIONS_WLANS_CREATE` | `UNIFI_PERMISSIONS_WLANS_UPDATE` | `UNIFI_PERMISSIONS_WLANS_DELETE` |
| devices | `UNIFI_PERMISSIONS_DEVICES_CREATE` | `UNIFI_PERMISSIONS_DEVICES_UPDATE` | `UNIFI_PERMISSIONS_DEVICES_DELETE` |
| clients | — | `UNIFI_PERMISSIONS_CLIENTS_UPDATE` | `UNIFI_PERMISSIONS_CLIENTS_DELETE` |
| firewall_policies | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE` | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_UPDATE` | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_DELETE` |
| traffic_routes | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_CREATE` | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_UPDATE` | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_DELETE` |
| port_forwards | `UNIFI_PERMISSIONS_PORT_FORWARDS_CREATE` | `UNIFI_PERMISSIONS_PORT_FORWARDS_UPDATE` | `UNIFI_PERMISSIONS_PORT_FORWARDS_DELETE` |
| qos_rules | `UNIFI_PERMISSIONS_QOS_RULES_CREATE` | `UNIFI_PERMISSIONS_QOS_RULES_UPDATE` | `UNIFI_PERMISSIONS_QOS_RULES_DELETE` |
| vpn_clients | `UNIFI_PERMISSIONS_VPN_CLIENTS_CREATE` | `UNIFI_PERMISSIONS_VPN_CLIENTS_UPDATE` | `UNIFI_PERMISSIONS_VPN_CLIENTS_DELETE` |
| vpn_servers | `UNIFI_PERMISSIONS_VPN_SERVERS_CREATE` | `UNIFI_PERMISSIONS_VPN_SERVERS_UPDATE` | `UNIFI_PERMISSIONS_VPN_SERVERS_DELETE` |
| acl_rules | `UNIFI_PERMISSIONS_ACL_RULES_CREATE` | `UNIFI_PERMISSIONS_ACL_RULES_UPDATE` | `UNIFI_PERMISSIONS_ACL_RULES_DELETE` |
| vouchers | `UNIFI_PERMISSIONS_VOUCHERS_CREATE` | `UNIFI_PERMISSIONS_VOUCHERS_UPDATE` | `UNIFI_PERMISSIONS_VOUCHERS_DELETE` |
| routes | `UNIFI_PERMISSIONS_ROUTES_CREATE` | `UNIFI_PERMISSIONS_ROUTES_UPDATE` | `UNIFI_PERMISSIONS_ROUTES_DELETE` |
| events | — | `UNIFI_PERMISSIONS_EVENTS_UPDATE` | — |
| usergroups | `UNIFI_PERMISSIONS_USERGROUPS_CREATE` | `UNIFI_PERMISSIONS_USERGROUPS_UPDATE` | `UNIFI_PERMISSIONS_USERGROUPS_DELETE` |
| snmp | — | `UNIFI_PERMISSIONS_SNMP_UPDATE` | — |

## Behavior by Registration Mode

| Mode | Denied tool visible? | Denied tool callable? |
|------|---------------------|----------------------|
| **eager** | Not in client tool list | No |
| **lazy** | In `unifi_tool_index` | No (returns permission error) |
| **meta_only** | In `unifi_tool_index` | No (returns permission error) |

If a tool you expect is missing from your client's tool list, the most common cause is a disabled permission.

## Confirmation System

All mutating tools use a **preview-then-confirm** pattern:

1. Call without `confirm` (default) — returns a preview of the change
2. Call with `confirm=true` — executes the mutation

Set `UNIFI_AUTO_CONFIRM=true` to skip previews for automation workflows (n8n, Make, Zapier).

| Level | Method | Use Case |
|-------|--------|----------|
| Per-call | `confirm=true` in arguments | LLM explicitly confirms |
| Per-session | System prompt instructs auto-confirm | Agent follows standing instructions |
| Per-environment | `UNIFI_AUTO_CONFIRM=true` | Workflow automation |
