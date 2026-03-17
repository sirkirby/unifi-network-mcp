# UniFi Access MCP Server

MCP server exposing UniFi Access tools for LLMs, agents, and automation platforms. Manage doors, credentials, access policies, visitors, events, and devices -- with safe-by-default permissions and preview-before-confirm for all mutations.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
# PyPI (recommended)
uvx unifi-access-mcp
# or: pip install unifi-access-mcp

# Docker
docker pull ghcr.io/sirkirby/unifi-access-mcp:latest

# From source
git clone https://github.com/sirkirby/unifi-mcp.git
cd unifi-mcp && uv sync
```

## Configure

Set these environment variables (or create a `.env` file):

```bash
# Server-specific variables (recommended)
UNIFI_ACCESS_HOST=192.168.1.1      # Controller IP or hostname
UNIFI_ACCESS_USERNAME=admin         # Local admin username
UNIFI_ACCESS_PASSWORD=your-password # Admin password
# Optional:
# UNIFI_ACCESS_API_KEY=             # Official UniFi API key (dual auth)
# UNIFI_ACCESS_PORT=443             # Controller HTTPS port
# UNIFI_ACCESS_VERIFY_SSL=false     # SSL certificate verification
```

**Fallback:** The shared `UNIFI_*` variables (e.g., `UNIFI_HOST`) also work. The server checks for `UNIFI_ACCESS_*` first and falls back to `UNIFI_*` if the server-specific variable is not set. For single-controller setups, the shared variables are all you need.

### Dual Authentication

The Access server supports two independent auth paths:

1. **API key** -- Uses `py-unifi-access` on the dedicated Access API port (default 12445). Best for read-only queries and device listing.
2. **Local proxy session** -- Logs in via `/api/auth/login` on the UniFi OS Console (port 443) and proxies requests through `/proxy/access/api/v2/...`. Required for door lock/unlock, credential management, policies, visitors, and events.

At least one path must be configured. When both are available, each tool selects the most appropriate path. Most mutating tools require the local proxy session.

## Run

```bash
# stdio transport (default -- for Claude Desktop, LM Studio, etc.)
unifi-access-mcp

# Docker
docker run -i --rm \
  -e UNIFI_ACCESS_HOST=192.168.1.1 \
  -e UNIFI_ACCESS_USERNAME=admin \
  -e UNIFI_ACCESS_PASSWORD=secret \
  ghcr.io/sirkirby/unifi-access-mcp:latest
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "unifi-access": {
      "command": "uvx",
      "args": ["unifi-access-mcp"],
      "env": {
        "UNIFI_ACCESS_HOST": "192.168.1.1",
        "UNIFI_ACCESS_USERNAME": "admin",
        "UNIFI_ACCESS_PASSWORD": "your-password"
      }
    }
  }
}
```

## Features

- **Doors** -- list, inspect, lock/unlock, door groups, real-time status
- **Policies** -- list, inspect, update access policies and schedules
- **Credentials** -- list, inspect, create, revoke NFC cards, PINs, mobile credentials
- **Visitors** -- list, inspect, create, delete visitor passes with time-bounded access
- **Events** -- query historical events, real-time websocket buffer, activity summaries
- **Devices** -- list, inspect, reboot access hubs, readers, relays, intercoms
- **System** -- controller info, health metrics, user listing

## Documentation

- [Configuration](docs/configuration.md) -- Full env var reference, YAML config, Access-specific options
- [Permissions](docs/permissions.md) -- Permission system, category defaults, how to enable mutations
- [Tool Catalog](docs/tools.md) -- All 29 tools organized by category
- [Event Streaming](docs/events.md) -- Real-time event architecture, WebSocket buffer, polling
- [Troubleshooting](docs/troubleshooting.md) -- Connection issues, dual auth debugging, missing tools

## Development

```bash
cd apps/access
make test         # Run tests
make lint         # Lint
make format       # Format
make manifest     # Regenerate tools_manifest.json
make console      # Start interactive dev console
make pre-commit   # All of the above
```

See the root [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full monorepo workflow.

## License

[MIT](../../LICENSE)
