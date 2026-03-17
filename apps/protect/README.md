# UniFi Protect MCP Server

MCP server exposing 34 UniFi Protect tools for LLMs, agents, and automation platforms. Query cameras, events, smart detections, recordings, lights, sensors, and chimes -- with safe-by-default permissions and preview-before-confirm for all mutations.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
# PyPI (recommended)
uvx unifi-protect-mcp
# or: pip install unifi-protect-mcp

# Docker
docker pull ghcr.io/sirkirby/unifi-protect-mcp:latest

# From source
git clone https://github.com/sirkirby/unifi-mcp.git
cd unifi-mcp && uv sync
```

## Configure

Set these environment variables (or create a `.env` file):

```bash
UNIFI_HOST=192.168.1.1      # Controller IP or hostname
UNIFI_USERNAME=admin         # Local admin username
UNIFI_PASSWORD=your-password # Admin password
# Optional:
# UNIFI_PORT=443             # Controller HTTPS port
# UNIFI_VERIFY_SSL=false     # SSL certificate verification
```

## Run

```bash
# stdio transport (default -- for Claude Desktop, LM Studio, etc.)
unifi-protect-mcp

# Docker
docker run -i --rm \
  -e UNIFI_HOST=192.168.1.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PASSWORD=secret \
  ghcr.io/sirkirby/unifi-protect-mcp:latest
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "unifi-protect": {
      "command": "uvx",
      "args": ["unifi-protect-mcp"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "your-password"
      }
    }
  }
}
```

## Features

- **Cameras** -- list, inspect, snapshot, RTSP streams, PTZ control, settings, recording toggle, reboot
- **Events** -- query historical events, smart detections (person/vehicle/animal/package), thumbnails
- **Real-time streaming** -- websocket event buffer with MCP resource subscriptions and polling
- **Recordings** -- status, availability, clip export with timelapse support
- **Devices** -- lights (brightness, PIR sensitivity), sensors (temperature, humidity, motion), chimes (volume, trigger)
- **Liveviews** -- list and inspect multi-camera layouts
- **System** -- NVR info, health metrics, firmware status, connected viewers

## Documentation

- [Configuration](docs/configuration.md) -- Full env var reference, YAML config, Protect-specific options
- [Permissions](docs/permissions.md) -- Permission system, category defaults, how to enable mutations
- [Tool Catalog](docs/tools.md) -- All 34 tools organized by category
- [Event Streaming](docs/events.md) -- Real-time event architecture, MCP resources, polling
- [Troubleshooting](docs/troubleshooting.md) -- Connection issues, SSL, missing tools

## Development

```bash
cd apps/protect
make test         # Run tests
make lint         # Lint
make format       # Format
make manifest     # Regenerate tools_manifest.json
make pre-commit   # All of the above
```

See the root [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full monorepo workflow.

## License

[MIT](../../LICENSE)
