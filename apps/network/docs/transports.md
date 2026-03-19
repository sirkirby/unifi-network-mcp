# Transport Setup

The server supports three transport protocols. stdio is the default and recommended for most use cases.

## stdio (Default)

Used by Claude Desktop, LM Studio, and most MCP clients. No configuration needed.

```bash
# Direct
unifi-network-mcp

# Via uvx
uvx unifi-network-mcp@latest

# Docker (stdin_open required)
docker run -i --rm \
  -e UNIFI_HOST=192.168.1.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PASSWORD=secret \
  ghcr.io/sirkirby/unifi-network-mcp:latest
```

### Claude Desktop Configuration

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

### Docker with Claude Desktop

Option A: Claude launches the container:
```jsonc
{
  "mcpServers": {
    "unifi": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "UNIFI_HOST=192.168.1.1",
        "-e", "UNIFI_USERNAME=admin",
        "-e", "UNIFI_PASSWORD=secret",
        "ghcr.io/sirkirby/unifi-network-mcp:latest"
      ]
    }
  }
}
```

Option B: Attach to a running container (via docker-compose):
```bash
docker compose -f docker/docker-compose.yml up -d
```
```jsonc
{
  "mcpServers": {
    "unifi": {
      "command": "docker",
      "args": ["exec", "-i", "unifi-network-mcp", "unifi-network-mcp"]
    }
  }
}
```

### LM Studio

Edit `mcp.json` (chat prompt > tool icon > edit mcp.json) with the same structure as Claude Desktop config above. Use a tool-capable model like `gpt-oss`.

## Streamable HTTP

The current MCP spec default (2025-03-26). Uses a single `/mcp` endpoint.

```bash
# Enable
export UNIFI_MCP_HTTP_ENABLED=true
# Transport defaults to streamable-http

# Optional: customize binding
export UNIFI_MCP_HOST=0.0.0.0
export UNIFI_MCP_PORT=3000
```

```bash
# Docker with HTTP
docker run -i --rm \
  -p 3000:3000 \
  -e UNIFI_MCP_HTTP_ENABLED=true \
  -e UNIFI_HOST=192.168.1.1 \
  -e UNIFI_USERNAME=admin \
  -e UNIFI_PASSWORD=secret \
  ghcr.io/sirkirby/unifi-network-mcp:latest
```

The endpoint supports:
- **POST** `/mcp` — JSON-RPC requests
- **GET** `/mcp` — SSE event stream
- **DELETE** `/mcp` — Session termination

stdio and HTTP can run concurrently.

## SSE (Legacy)

For backwards compatibility with older MCP clients.

```bash
export UNIFI_MCP_HTTP_ENABLED=true
export UNIFI_MCP_HTTP_TRANSPORT=sse
```

Uses `/sse` (event stream) + `/messages/` (JSON-RPC) endpoints.

## Reverse Proxy

When running behind Nginx, Cloudflare, or a Kubernetes ingress:

1. Add your domain to allowed hosts:
   ```bash
   export UNIFI_MCP_ALLOWED_HOSTS=localhost,127.0.0.1,unifi-mcp.example.com
   ```

2. If host validation still fails, disable DNS rebinding protection (trusted networks only):
   ```bash
   export UNIFI_MCP_ENABLE_DNS_REBINDING_PROTECTION=false
   ```

## Security Notes

- **stdio** is the safest transport — no network exposure
- **HTTP** should only be enabled in local development or behind authenticated reverse proxies
- Leave HTTP disabled in production unless you understand the security implications
- When using HTTP, consider enabling only for container environments (HTTP auto-starts for PID 1 processes; use `UNIFI_MCP_HTTP_FORCE=true` to override)
