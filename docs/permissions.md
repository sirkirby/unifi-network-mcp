# Permission System

The UniFi Network MCP server includes a comprehensive permission system that allows you to control which tools are available based on the risk level of their operations.

## Overview

Permissions are enforced at **decorator-level** during tool registration. Tools that don't meet the permission requirements are **never registered** with the MCP server, making them completely unavailable to LLMs.

This is a security-critical feature that prevents accidental or unauthorized modifications to your network infrastructure.

## How It Works

### 1. Permission Configuration

Permissions are configured in `src/config/config.yaml`:

```yaml
permissions:
  default:
    create: true
    update: true

  networks:
    create: false  # Provisioning a new network can disrupt traffic
    update: false  # Changing subnets, VLANs, DHCP ranges requires care

  devices:
    create: false  # Adoption/provisioning
    update: false  # Firmware upgrades, renames, etc.

  clients:
    create: false  # Not applicable
    update: false  # Block/unblock, reconnect, etc.
```

### 2. Tool Decorators

Tools specify their permission requirements using decorator parameters:

```python
@server.tool(
    name="unifi_create_network",
    description="Create a new network (LAN/VLAN)",
    permission_category="networks",
    permission_action="create"
)
async def create_network(network_data: dict):
    # This tool will NOT be registered if permissions.networks.create = false
    ...
```

### 3. Enforcement

The `permissioned_tool` decorator in `src/main.py` checks permissions **before** registering tools:

```python
# Check permission config
allowed = parse_permission(config.permissions, category, action)

if allowed:
    # Register tool with MCP server
    register_tool(...)
    return _original_tool_decorator(...)(func)
else:
    # Skip registration - tool won't be available
    logger.info("[permissions] Skipping registration of tool '%s'", tool_name)
    return func
```

## Permission Categories

| Category | Default | Description |
|----------|---------|-------------|
| **networks** | ❌ Disabled | Network creation/modification (high risk) |
| **wlans** | ❌ Disabled | Wireless network configuration (high risk) |
| **devices** | ❌ Disabled | Device adoption, upgrades, reboots (high risk) |
| **clients** | ❌ Disabled | Client blocking, reconnection (medium risk) |
| **vpn_servers** | Create: ❌ Update: ✅ | VPN server configuration |
| **firewall_policies** | ✅ Enabled | Firewall rule management |
| **traffic_routes** | ✅ Enabled | Static route configuration |
| **port_forwards** | ✅ Enabled | Port forwarding rules |
| **qos_rules** | ✅ Enabled | Quality of Service rules |
| **vpn_clients** | ✅ Enabled | VPN client configuration |

## Default Configuration Rationale

The default configuration is **conservative** and prioritizes network stability:

### Disabled by Default (High Risk)

- **networks**: Creating/modifying networks can cause network outages
- **wlans**: Wireless changes can disconnect all Wi-Fi clients
- **devices**: Device upgrades can cause downtime
- **clients**: Client operations affect user connectivity

### Enabled by Default (Lower Risk)

- **firewall_policies**: Typically additive (allow rules)
- **traffic_routes**: Well-scoped changes
- **port_forwards**: Isolated impact
- **qos_rules**: Performance tuning, non-breaking

## Enabling Permissions

You can enable permissions in three ways (in priority order):

### 1. Environment Variables (Highest Priority) ⭐ **RECOMMENDED**

Enable specific permissions at runtime without modifying config files:

```bash
# Enable network creation
export UNIFI_PERMISSIONS_NETWORKS_CREATE=true
export UNIFI_PERMISSIONS_NETWORKS_UPDATE=true

# Enable device management
export UNIFI_PERMISSIONS_DEVICES_CREATE=true
export UNIFI_PERMISSIONS_DEVICES_UPDATE=true

# Enable client operations
export UNIFI_PERMISSIONS_CLIENTS_UPDATE=true
```

**For Claude Desktop**, add to your MCP server config:

```json
{
  "mcpServers": {
    "unifi": {
      "command": "uv",
      "args": ["--directory", "/path/to/unifi-network-mcp", "run", "python", "-m", "src.main"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "password",
        "UNIFI_PERMISSIONS_NETWORKS_CREATE": "true",
        "UNIFI_PERMISSIONS_DEVICES_UPDATE": "true"
      }
    }
  }
}
```

### 2. Config File

Modify `src/config/config.yaml`:

```yaml
permissions:
  networks:
    create: true
    update: true

  devices:
    create: true
    update: true
```

### 3. Default Permissions

Falls back to the defaults in config.yaml if no overrides are set.

## Permission Variable Names

Environment variables follow the pattern: `UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>`

| Category | Create Variable | Update Variable |
|----------|----------------|-----------------|
| **networks** | `UNIFI_PERMISSIONS_NETWORKS_CREATE` | `UNIFI_PERMISSIONS_NETWORKS_UPDATE` |
| **wlans** | `UNIFI_PERMISSIONS_WLANS_CREATE` | `UNIFI_PERMISSIONS_WLANS_UPDATE` |
| **devices** | `UNIFI_PERMISSIONS_DEVICES_CREATE` | `UNIFI_PERMISSIONS_DEVICES_UPDATE` |
| **clients** | N/A | `UNIFI_PERMISSIONS_CLIENTS_UPDATE` |
| **firewall_policies** | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE` | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_UPDATE` |
| **traffic_routes** | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_CREATE` | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_UPDATE` |
| **port_forwards** | `UNIFI_PERMISSIONS_PORT_FORWARDS_CREATE` | `UNIFI_PERMISSIONS_PORT_FORWARDS_UPDATE` |
| **qos_rules** | `UNIFI_PERMISSIONS_QOS_RULES_CREATE` | `UNIFI_PERMISSIONS_QOS_RULES_UPDATE` |
| **vpn_clients** | `UNIFI_PERMISSIONS_VPN_CLIENTS_CREATE` | `UNIFI_PERMISSIONS_VPN_CLIENTS_UPDATE` |
| **vpn_servers** | `UNIFI_PERMISSIONS_VPN_SERVERS_CREATE` | `UNIFI_PERMISSIONS_VPN_SERVERS_UPDATE` |

**Accepted Values:** `true`, `1`, `yes`, `on` (case-insensitive) = enabled; anything else = disabled

## Impact on Tool Discovery and Availability

**Important:** Permissions directly control which tools your MCP client (e.g., Claude Desktop) can see and use.

The tool manifest (`tools_manifest.json`) always includes all tools regardless of permission settings. However, permissions determine what is actually registered with the MCP server at startup:

### How It Works

When the server starts:

1. **All tools added to the TOOL_REGISTRY** (internal index for `unifi_tool_index` discovery)
2. **Permission check determines MCP registration** (what your client sees):
   - ✅ Allowed: Tool is registered with the MCP server and callable
   - ❌ Denied: Tool is **not registered** — it will not appear in your client's tool list and cannot be called directly

Example server startup output:

```
[permissions] Skipping MCP registration of tool 'unifi_create_network' (category=networks, action=create)
[permissions] Skipping MCP registration of tool 'unifi_adopt_device' (category=devices, action=create)
...
```

### What This Means for Each Registration Mode

| Mode | Disabled tool visible? | Disabled tool callable? |
|------|----------------------|------------------------|
| **eager** | Not in client tool list | No |
| **lazy** | Discoverable via `unifi_tool_index` | No — returns permission error via `unifi_execute` |
| **meta_only** | Discoverable via `unifi_tool_index` | No — returns permission error via `unifi_execute` |

**Key takeaway:** If you are using **eager mode** and a tool is missing from your client, the most likely cause is that its permission is disabled. Enable the relevant permission and restart the server.

In **lazy** and **meta_only** modes, all tools always appear in `unifi_tool_index` results (since the index reads from the static manifest), but disabled tools will return a permission error when called through `unifi_execute`.

**Why this design:**
- Users configure their own permissions
- Tool manifest is consistent across installations
- No rebuild required when changing permissions
- Clear feedback about what's available vs. what's allowed

## Security Benefits

1. **Defense in Depth** - Permissions enforced at multiple levels:
   - Build time (manifest generation)
   - Runtime (decorator evaluation)

2. **Fail-Safe Defaults** - High-risk operations disabled by default

3. **Visibility** - Clear logging of permission decisions

4. **Atomic Control** - Enable/disable entire categories at once

## Permission Actions

| Action | Typical Operations |
|--------|-------------------|
| **create** | Add new resources (networks, rules, etc.) |
| **update** | Modify existing resources (rename, toggle, change config) |
| **delete** | Remove resources (typically uses "update" permission) |

Note: `delete` operations typically use the `update` permission since they modify the resource list.

## Tools by Permission

### Networks (Disabled by Default)
- ❌ `unifi_create_network`
- ❌ `unifi_update_network`
- ✅ `unifi_list_networks` (no permission required)
- ✅ `unifi_get_network_details` (no permission required)

### WLANs (Disabled by Default)
- ❌ `unifi_create_wlan`
- ❌ `unifi_update_wlan`
- ✅ `unifi_list_wlans` (no permission required)

### Devices (Disabled by Default)
- ❌ `unifi_adopt_device`
- ❌ `unifi_upgrade_device`
- ❌ `unifi_reboot_device`
- ❌ `unifi_rename_device`
- ✅ `unifi_list_devices` (no permission required)

### Clients (Disabled by Default)
- ❌ `unifi_block_client`
- ❌ `unifi_unblock_client`
- ❌ `unifi_force_reconnect_client`
- ❌ `unifi_authorize_guest`
- ❌ `unifi_unauthorize_guest`
- ✅ `unifi_list_clients` (no permission required)
- ✅ `unifi_rename_client` (no permission check)

### Firewall Policies (Enabled by Default)
- ✅ `unifi_create_firewall_policy`
- ✅ `unifi_update_firewall_policy`
- ✅ `unifi_toggle_firewall_policy`
- ✅ `unifi_create_simple_firewall_policy`

### Traffic Routes (Enabled by Default)
- ✅ `unifi_create_traffic_route`
- ✅ `unifi_update_traffic_route`
- ✅ `unifi_toggle_traffic_route`
- ✅ `unifi_create_simple_traffic_route`

### Port Forwards (Enabled by Default)
- ✅ `unifi_create_port_forward`
- ✅ `unifi_update_port_forward`
- ✅ `unifi_toggle_port_forward`
- ✅ `unifi_create_simple_port_forward`

### QoS Rules (Enabled by Default)
- ✅ `unifi_create_qos_rule`
- ✅ `unifi_update_qos_rule`
- ✅ `unifi_toggle_qos_rule_enabled`
- ✅ `unifi_create_simple_qos_rule`

### VPN (Mixed)
- ✅ `unifi_update_vpn_client_state` (vpn_clients: enabled)
- ✅ `unifi_update_vpn_server_state` (vpn_servers: update only)

## Best Practices

1. **Start Conservative** - Use default permissions initially
2. **Enable Selectively** - Only enable what you need
3. **Test First** - Enable in dev/test environments before production
4. **Document Changes** - Track permission changes in version control
5. **Review Regularly** - Audit enabled permissions periodically

## Troubleshooting

### Tool Missing from Client Tool List (Eager Mode)

**Symptom:** A tool you expect to see is not listed by your MCP client (e.g., Claude Desktop)

**Cause:** The tool's permission is disabled, so it was not registered with the MCP server at startup.

**Solution:**
1. Enable the relevant permission via environment variable (e.g., `UNIFI_PERMISSIONS_NETWORKS_CREATE=true`)
2. Restart the MCP server
3. The tool will now appear in your client's tool list

### Tool Returns "Permission Denied" via unifi_execute (Lazy/Meta-Only Mode)

**Symptom:** Tool appears in `unifi_tool_index` but returns a permission error when called through `unifi_execute`

**Cause:** The tool's permission is disabled. In lazy/meta-only mode, `unifi_tool_index` reads from the static manifest (which includes all tools), but the tool's internal permission check blocks execution.

**Solution:**
1. Enable the relevant permission via environment variable
2. Restart the MCP server

### Permission Denied at Runtime

**Symptom:** "Permission denied" error when calling a tool that IS registered

**Cause:** Some tools have additional runtime permission checks beyond the decorator-level check

**Solution:** Check both:
- Decorator permissions (category/action level in config.yaml or env vars)
- Runtime permission checks (within the tool function, e.g., `client.block` vs `client.update`)

## Future Enhancements

Planned for future releases:

1. **Fine-grained permissions** - Per-tool overrides
2. **Permission profiles** - Predefined sets (e.g., "read-only", "power-user")
3. **Dynamic permissions** - Runtime permission changes without restart
4. **Audit logging** - Track all permission-gated operations

## Confirmation System

All mutating tools (create, update, toggle, delete operations) implement a **preview-then-confirm** pattern for safety:

### How It Works

1. **Without confirmation** (`confirm=false`, the default): Tool returns a preview of what will change
2. **With confirmation** (`confirm=true`): Tool executes the operation

**Example preview response:**
```json
{
  "success": false,
  "requires_confirmation": true,
  "action": "toggle",
  "resource_type": "port_forward",
  "resource_id": "abc123",
  "resource_name": "SSH Access",
  "preview": {
    "current": {"enabled": true},
    "proposed": {"enabled": false}
  },
  "message": "Will disable port_forward 'SSH Access'. Set confirm=true to execute."
}
```

This gives LLM agents context to make informed decisions before executing changes.

### Three Levels of Confirmation Control

| Level | Method | Use Case |
|-------|--------|----------|
| **Per-call** | Pass `confirm=true` in tool arguments | LLM explicitly confirms each operation |
| **Per-session** | System prompt instructs agent to auto-confirm | Agent follows user's standing instructions |
| **Per-environment** | `UNIFI_AUTO_CONFIRM=true` env var | Workflow automation (n8n, Make, Zapier) |

### Auto-Confirm for Workflow Automation

For workflow automation tools where the two-step confirmation adds unnecessary complexity:

**Environment variable:**
```bash
export UNIFI_AUTO_CONFIRM=true
```

**Docker:**
```bash
docker run -e UNIFI_AUTO_CONFIRM=true ...
```

**Claude Desktop / n8n:**
```json
{
  "env": {
    "UNIFI_AUTO_CONFIRM": "true"
  }
}
```

When `UNIFI_AUTO_CONFIRM=true`:
- All mutating operations execute immediately
- Preview step is skipped
- No changes to your workflow logic required

**Accepted values:** `true`, `1`, `yes` (case-insensitive)

### Dev Console Behavior

The developer console (`devtools/dev_console.py`) automatically sets `confirm=true` for testing convenience, displaying a warning:

```
⚠️  DEV CONSOLE: Auto-setting confirm=true for testing
   (In production, LLMs must explicitly confirm operations)
```

This makes testing faster while reminding developers about production behavior.

## Related Documentation

- [Configuration Guide](configuration.md)
- [Security Best Practices](security.md)
- [Tool Index API](tool-index.md)
