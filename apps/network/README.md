# UniFi Network MCP Server

MCP server exposing 91 UniFi Network Controller tools for LLMs, agents, and automation platforms. Query clients, devices, firewall rules, VLANs, VPNs, stats, and more — with safe-by-default permissions and preview-before-confirm for all mutations.

## Install

```bash
# PyPI (recommended)
uvx unifi-network-mcp
# or: pip install unifi-network-mcp

# Docker
docker pull ghcr.io/sirkirby/unifi-network-mcp:latest

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
# UNIFI_API_KEY=             # Official UniFi API key (dual auth)
# UNIFI_PORT=443             # Controller HTTPS port
# UNIFI_SITE=default         # UniFi site name
# UNIFI_VERIFY_SSL=false     # SSL certificate verification
```

## Run

```bash
# stdio transport (default — for Claude Desktop, LM Studio, etc.)
unifi-network-mcp

# Docker
docker run -i --rm \
  -e UNIFI_HOST=192.168.1.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PASSWORD=secret \
  ghcr.io/sirkirby/unifi-network-mcp:latest
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "unifi": {
      "command": "uvx",
      "args": ["unifi-network-mcp"],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "your-password"
      }
    }
  }
}
```

## Documentation

- [Configuration](docs/configuration.md) — Full env var reference, YAML config, controller type detection
- [Permissions](docs/permissions.md) — Permission system, category defaults, how to enable high-risk tools
- [Tool Catalog](docs/tools.md) — All 91 tools organized by category
- [Transports](docs/transports.md) — stdio, Streamable HTTP, and SSE setup
- [Troubleshooting](docs/troubleshooting.md) — Connection issues, SSL, missing tools

## Development

```bash
cd apps/network
make test         # Run tests
make lint         # Lint
make format       # Format
make manifest     # Regenerate tools_manifest.json
make pre-commit   # All of the above
```

See the root [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full monorepo workflow.

## License

[MIT](../../LICENSE)
