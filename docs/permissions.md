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

**Important:** Permissions are enforced at **runtime**, not build time!

The tool manifest (`tools_manifest.json`) **always includes all 64 tools** regardless of permission settings. This ensures:

1. ✅ **Users control permissions** via their own config.yaml
2. ✅ **LLMs can discover all tools** via `unifi_tool_index`
3. ✅ **Disabled tools appear in index but are not callable**
4. ✅ **Permissions enforced when tools are called**

### How It Works

When the server starts:

1. **All tools registered in TOOL_REGISTRY** (for discovery)
2. **Permission check determines MCP registration**:
   - ✅ Allowed: Tool is callable via MCP
   - ❌ Denied: Tool appears in index but returns permission error

Example server startup output:

```
[permissions] Skipping MCP registration of tool 'unifi_create_network' (category=networks, action=create)
[permissions] Skipping MCP registration of tool 'unifi_adopt_device' (category=devices, action=create)
...
```

### User Experience

**If a tool is disabled:**
- ✅ Appears in `unifi_tool_index` results
- ❌ Cannot be called via MCP (not registered with server)
- 💡 LLM will see it exists but cannot invoke it

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

### Tool Not Appearing in tool_index

**Symptom:** A tool is missing from `unifi_tool_index` results

**Cause:** Permission is set to `false` in config.yaml

**Solution:**
1. Check `src/config/config.yaml` for the permission setting
2. Enable the permission if appropriate
3. Regenerate manifest: `make manifest`
4. Restart the MCP server

### Permission Denied at Runtime

**Symptom:** "Permission denied" error when calling a tool

**Cause:** Some tools have additional runtime permission checks

**Solution:** Check both:
- Decorator permissions (config.yaml)
- Runtime permission checks (within tool function)

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
