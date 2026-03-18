# Setup and Configuration

How to install, configure, and run the UniFi MCP servers. For deeper details, each server has its own documentation in `apps/<server>/docs/`.

## Table of Contents
- [Installation](#installation)
- [Claude Desktop Configuration](#claude-desktop-configuration)
- [Environment Variables](#environment-variables)
- [Multi-Controller Setup](#multi-controller-setup)
- [Permission Configuration](#permission-configuration)
- [Transport Modes](#transport-modes)
- [Tool Registration Modes](#tool-registration-modes)
- [Troubleshooting](#troubleshooting)

---

## Installation

Each server is an independent Python package. Install and run with `uvx` (no pip install needed):

```bash
uvx unifi-network-mcp    # Network server (stable)
uvx unifi-protect-mcp    # Protect server (beta)
uvx unifi-access-mcp     # Access server (beta)
```

Or via Docker:
```bash
docker pull ghcr.io/sirkirby/unifi-network-mcp:latest
docker pull ghcr.io/sirkirby/unifi-protect-mcp:latest
docker pull ghcr.io/sirkirby/unifi-access-mcp:latest
```

---

## Claude Desktop Configuration

Each server gets its own block in `claude_desktop_config.json`. Here's a full example with all three servers:

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-network-mcp"],
      "env": {
        "UNIFI_NETWORK_HOST": "192.168.1.1",
        "UNIFI_NETWORK_USERNAME": "admin",
        "UNIFI_NETWORK_PASSWORD": "your-password"
      }
    },
    "unifi-protect": {
      "command": "uvx",
      "args": ["unifi-protect-mcp"],
      "env": {
        "UNIFI_PROTECT_HOST": "192.168.1.1",
        "UNIFI_PROTECT_USERNAME": "admin",
        "UNIFI_PROTECT_PASSWORD": "your-password"
      }
    },
    "unifi-access": {
      "command": "uvx",
      "args": ["unifi-access-mcp"],
      "env": {
        "UNIFI_ACCESS_HOST": "192.168.1.1",
        "UNIFI_ACCESS_USERNAME": "admin",
        "UNIFI_ACCESS_PASSWORD": "your-password",
        "UNIFI_ACCESS_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Single-controller shortcut:** If all servers connect to the same controller, you can use the shared `UNIFI_*` prefix instead of server-specific ones. Each server falls back to the shared prefix when its own isn't set.

---

## Environment Variables

### Connection (per server)

Each server supports its own prefixed variables that override the shared `UNIFI_*` fallback.

| Setting | Network | Protect | Access | Shared Fallback | Default |
|---------|---------|---------|--------|-----------------|---------|
| Host | `UNIFI_NETWORK_HOST` | `UNIFI_PROTECT_HOST` | `UNIFI_ACCESS_HOST` | `UNIFI_HOST` | (required) |
| Username | `UNIFI_NETWORK_USERNAME` | `UNIFI_PROTECT_USERNAME` | `UNIFI_ACCESS_USERNAME` | `UNIFI_USERNAME` | (required*) |
| Password | `UNIFI_NETWORK_PASSWORD` | `UNIFI_PROTECT_PASSWORD` | `UNIFI_ACCESS_PASSWORD` | `UNIFI_PASSWORD` | (required*) |
| API Key | `UNIFI_NETWORK_API_KEY` | `UNIFI_PROTECT_API_KEY` | `UNIFI_ACCESS_API_KEY` | `UNIFI_API_KEY` | (optional) |
| Port | `UNIFI_NETWORK_PORT` | `UNIFI_PROTECT_PORT` | `UNIFI_ACCESS_PORT` | `UNIFI_PORT` | 443 |
| Verify SSL | `UNIFI_NETWORK_VERIFY_SSL` | `UNIFI_PROTECT_VERIFY_SSL` | `UNIFI_ACCESS_VERIFY_SSL` | `UNIFI_VERIFY_SSL` | false |

*Username and password are required for local auth. If using API key auth only, they may be optional depending on the server.

**Resolution order:** Server-specific (`UNIFI_NETWORK_*`) > Shared (`UNIFI_*`) > Config YAML > Hardcoded default

### Server Settings (shared across all servers)

| Variable | Default | Purpose |
|----------|---------|---------|
| `UNIFI_MCP_LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `UNIFI_TOOL_REGISTRATION_MODE` | lazy | How tools are loaded: lazy, eager, or meta_only |
| `UNIFI_AUTO_CONFIRM` | false | Skip preview step for mutations (for automation) |
| `UNIFI_MCP_HTTP_ENABLED` | false | Enable HTTP transport alongside stdio |
| `UNIFI_MCP_HTTP_TRANSPORT` | streamable-http | HTTP transport type: streamable-http or sse |
| `UNIFI_MCP_HOST` | 0.0.0.0 | HTTP bind address |
| `UNIFI_MCP_PORT` | varies | HTTP port: 3000 (Network), 3001 (Protect), 3002 (Access) |

### Network-Specific

| Variable | Default | Purpose |
|----------|---------|---------|
| `UNIFI_NETWORK_SITE` | default | UniFi site name |
| `UNIFI_CONTROLLER_TYPE` | auto | Controller type detection: auto, proxy, or direct |

### Protect-Specific

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROTECT_EVENT_BUFFER_SIZE` | 100 | Websocket event ring buffer capacity |
| `PROTECT_EVENT_BUFFER_TTL` | 300 | Buffer event TTL in seconds |
| `PROTECT_WEBSOCKET_ENABLED` | true | Enable real-time event websocket |
| `PROTECT_SMART_DETECTION_MIN_CONFIDENCE` | 50 | Minimum confidence score (0-100) for smart detections |

### Access-Specific

| Variable | Default | Purpose |
|----------|---------|---------|
| `UNIFI_ACCESS_API_PORT` | 12445 | Dedicated Access API port (for API key path) |
| `ACCESS_EVENT_BUFFER_SIZE` | 100 | Websocket event ring buffer capacity |
| `ACCESS_EVENT_BUFFER_TTL` | 300 | Buffer event TTL in seconds |
| `ACCESS_WEBSOCKET_ENABLED` | true | Enable real-time event websocket |

---

## Multi-Controller Setup

If your UniFi devices are managed by different controllers (e.g., network on one, cameras on another), use server-specific prefixes:

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-network-mcp"],
      "env": {
        "UNIFI_NETWORK_HOST": "10.0.0.1",
        "UNIFI_NETWORK_USERNAME": "network-admin",
        "UNIFI_NETWORK_PASSWORD": "network-pass"
      }
    },
    "unifi-protect": {
      "command": "uvx",
      "args": ["unifi-protect-mcp"],
      "env": {
        "UNIFI_PROTECT_HOST": "10.0.0.2",
        "UNIFI_PROTECT_USERNAME": "protect-admin",
        "UNIFI_PROTECT_PASSWORD": "protect-pass"
      }
    }
  }
}
```

---

## Permission Configuration

Permissions control which mutations are allowed. The pattern is:

```
UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>=true
```

### Network Server Defaults

**Enabled by default** (create + update):
- `firewall_policies`, `traffic_routes`, `port_forwards`, `qos_rules`, `vpn_clients`, `acl_rules`, `vouchers`, `usergroups`

**Disabled by default** (require explicit opt-in):
- `networks`, `wlans`, `devices`, `clients`, `routes`, `vpn_servers`

**Delete is always disabled** across all categories.

### Protect Server Defaults

**All mutations disabled by default.** Enable selectively:
```bash
UNIFI_PERMISSIONS_CAMERAS_UPDATE=true      # Camera settings, recording, PTZ, reboot
UNIFI_PERMISSIONS_LIGHTS_UPDATE=true       # Light brightness, PIR, duration
UNIFI_PERMISSIONS_CHIMES_UPDATE=true       # Chime volume, trigger
UNIFI_PERMISSIONS_EVENTS_UPDATE=true       # Acknowledge events
UNIFI_PERMISSIONS_RECORDINGS_CREATE=true   # Export clips
```

### Access Server Defaults

**All mutations disabled by default.** Enable selectively:
```bash
UNIFI_PERMISSIONS_DOORS_UPDATE=true        # Lock/unlock doors
UNIFI_PERMISSIONS_POLICIES_UPDATE=true     # Update access policies
UNIFI_PERMISSIONS_CREDENTIALS_CREATE=true  # Create NFC/PIN/mobile credentials
UNIFI_PERMISSIONS_CREDENTIALS_DELETE=true  # Revoke credentials
UNIFI_PERMISSIONS_VISITORS_CREATE=true     # Create visitor passes
UNIFI_PERMISSIONS_VISITORS_DELETE=true     # Delete visitor passes
UNIFI_PERMISSIONS_DEVICES_UPDATE=true      # Reboot devices
```

### Automation Mode

For headless automation (n8n, Make, Zapier), combine permissions with auto-confirm:
```bash
UNIFI_AUTO_CONFIRM=true                     # Skip preview step
UNIFI_TOOL_REGISTRATION_MODE=eager          # All tools available immediately
UNIFI_PERMISSIONS_NETWORKS_CREATE=true      # Enable what you need
```

---

## Transport Modes

### stdio (Default — Always Active)

Used by Claude Desktop, LM Studio, and local LLMs. No configuration needed — it just works over stdin/stdout.

### HTTP (Optional)

Enable for remote clients or automation platforms:

```bash
UNIFI_MCP_HTTP_ENABLED=true
UNIFI_MCP_HTTP_TRANSPORT=streamable-http    # Recommended (MCP spec 2025-03-26)
UNIFI_MCP_PORT=3000                          # Or 3001/3002 for Protect/Access
```

Security settings for HTTP:
```bash
UNIFI_MCP_ALLOWED_HOSTS=localhost,127.0.0.1       # Allowed origins
UNIFI_MCP_ENABLE_DNS_REBINDING_PROTECTION=true    # DNS rebinding protection
```

stdio and HTTP can run concurrently — useful for serving both local and remote clients.

---

## Tool Registration Modes

| Mode | Context Cost | Behavior | Best For |
|------|-------------|----------|----------|
| `lazy` (default) | ~200 tokens | Meta-tools only; others load on demand | LLM clients (Claude Desktop) |
| `eager` | ~5,000 tokens | All tools registered immediately | Automation, dev console, testing |
| `meta_only` | ~200 tokens | Only meta-tools; use `*_execute` for everything | Maximum token savings |

Set via: `UNIFI_TOOL_REGISTRATION_MODE=lazy`

In `eager` mode, you can also filter which tools load:
```bash
UNIFI_ENABLED_CATEGORIES=clients,devices,system    # Only load these categories
UNIFI_ENABLED_TOOLS=unifi_list_clients,unifi_get_system_info   # Only these specific tools
```

---

## Troubleshooting

### Connection Fails

1. **Verify the host is reachable:** Can you access `https://<host>` in a browser?
2. **Check credentials:** Username/password correct? API key valid?
3. **SSL issues:** Set `UNIFI_VERIFY_SSL=false` for self-signed certs (default)
4. **Controller type:** Try `UNIFI_CONTROLLER_TYPE=proxy` or `direct` if `auto` detection fails

### Tools Not Available

1. **Check registration mode:** In `lazy` mode, use `*_tool_index` to discover tools, then `*_execute` to call them
2. **Check permissions:** A permission error means the tool is registered but the action is denied. Set the appropriate `UNIFI_PERMISSIONS_*` variable
3. **Check categories:** In `eager` mode with `UNIFI_ENABLED_CATEGORIES`, make sure your category is included

### Access Server Auth Issues

Access uses dual authentication:
- **API key path (port 12445):** Works for reads. Set `UNIFI_ACCESS_API_KEY`
- **Proxy session (port 443):** Required for mutations. Set `UNIFI_ACCESS_USERNAME` + `UNIFI_ACCESS_PASSWORD`

If mutations fail but reads work, you likely need proxy session credentials.

### Detailed Docs

For server-specific troubleshooting:
- Network: `apps/network/docs/troubleshooting.md`
- Protect: `apps/protect/docs/troubleshooting.md`
- Access: `apps/access/docs/troubleshooting.md`

For full configuration reference:
- Network: `apps/network/docs/configuration.md`
- Protect: `apps/protect/docs/configuration.md`
- Access: `apps/access/docs/configuration.md`
