# Quick Start Guide - v0.2.0

## 🚀 New in v0.2.0: Lazy Tool Loading is Now Default!

Save 96% on tokens with automatic on-demand tool loading - **active by default!**

---

## Installation

```bash
# Clone
git clone https://github.com/sirkirby/unifi-network-mcp.git
cd unifi-network-mcp

# Install
uv sync

# Configure
cat > .env << EOF
UNIFI_HOST=192.168.1.1
UNIFI_USERNAME=admin
UNIFI_PASSWORD=password
# UNIFI_TOOL_REGISTRATION_MODE=lazy  # This is the default - no need to set!
EOF
```

---

## Configuration Modes

### 🎯 Lazy Mode (DEFAULT) ⭐⭐⭐

**Active by default in v0.2.0!**

**Best for:** Claude Desktop, production LLMs, most users

**Config:**
```json
{
  "env": {
    // No need to set UNIFI_TOOL_REGISTRATION_MODE - defaults to "lazy"!
  }
}
```

**Benefits:**
- 96% token savings
- Tools load automatically when called
- Seamless UX
- **Active by default - no configuration needed!**

### Eager Mode

**Best for:** Dev console, automation, upgrading from v0.1.x

**Config:**
```json
{
  "env": {
    "UNIFI_TOOL_REGISTRATION_MODE": "eager"
  }
}
```

**Benefits:**
- All tools immediately available
- No lazy loading overhead
- Previous default behavior (v0.1.x)

### Meta-Only Mode

**Best for:** Maximum control

**Config:**
```json
{
  "env": {
    "UNIFI_TOOL_REGISTRATION_MODE": "meta_only"
  }
}
```

**Benefits:**
- 96% token savings
- Manual tool discovery via `unifi_tool_index`

---

## Quick Test

```bash
# Test with dev console
uv run python devtools/dev_console.py

# Test with Python examples
uv run python examples/python/query_tool_index.py
uv run python examples/python/use_async_jobs.py
uv run python examples/python/programmatic_client.py

# Run tests
uv run pytest tests/test_async_jobs.py -v
```

---

## Claude Desktop Setup

**1. Edit config:**
```bash
# macOS
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows
notepad %APPDATA%\Claude\claude_desktop_config.json
```

**2. Add server (lazy mode - default, recommended):**
```json
{
  "mcpServers": {
    "unifi": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/unifi-network-mcp",
        "run",
        "python",
        "-m",
        "src.main"
      ],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "password"
        // UNIFI_TOOL_REGISTRATION_MODE defaults to "lazy"
      }
    }
  }
}
```

**OR: Add server (eager mode - for v0.1.x compatibility):**
```json
{
  "mcpServers": {
    "unifi": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/unifi-network-mcp",
        "run",
        "python",
        "-m",
        "src.main"
      ],
      "env": {
        "UNIFI_HOST": "192.168.1.1",
        "UNIFI_USERNAME": "admin",
        "UNIFI_PASSWORD": "password",
        "UNIFI_TOOL_REGISTRATION_MODE": "eager"
      }
    }
  }
}
```

**3. Restart Claude Desktop**

**4. Test:**
- Ask: "What UniFi tools are available?"
- Ask: "Show me my wireless clients"
- Ask: "List all my devices"

---

## Token Savings

| Mode | Initial Tokens | After Query | Savings | Status |
|------|----------------|-------------|---------|--------|
| **lazy** (default) | **225** | **225** | **96%** | ⭐ **DEFAULT** |
| meta_only | 225 | 525 | 89% | |
| eager (v0.1.x) | 5,000 | 5,000 | 0% | Legacy |

---

## Key Features

### 1. Tool Index
```python
# Get all available tools with schemas
await server.call_tool("unifi_tool_index", {})
```

### 2. Tool Execution
```python
# Single execution (returns result directly)
result = await server.call_tool("unifi_execute", {
    "tool": "unifi_list_clients",
    "arguments": {}
})

# Batch execution (parallel, returns job IDs)
batch = await server.call_tool("unifi_batch", {
    "operations": [
        {"tool": "unifi_get_client_details", "arguments": {"mac": "aa:bb:cc:dd:ee:ff"}},
        {"tool": "unifi_get_device_details", "arguments": {"mac": "11:22:33:44:55:66"}}
    ]
})

# Check batch status
status = await server.call_tool("unifi_batch_status", {
    "jobIds": [job["jobId"] for job in batch["jobs"]]
})
```

### 3. Lazy Loading
```python
# Tools load automatically when called
result = await server.call_tool("unifi_list_devices", {})
# → Devices module loads on-demand
# → Tool executes normally
# → Cached for future calls
```

---

## Troubleshooting

### Issue: "I upgraded to v0.2.0 and now I only see 3 tools instead of 67!"

**Explanation:** Lazy mode is now the default! Tools are loaded automatically when called.

**Solution 1 (Recommended):** Just use the tools normally - they'll load on-demand:
- Ask Claude: "List my UniFi devices"
- The `unifi_list_devices` tool loads automatically
- All subsequent calls are instant

**Solution 2:** Restore v0.1.x behavior (eager mode):
```json
{
  "env": {
    "UNIFI_TOOL_REGISTRATION_MODE": "eager"
  }
}
```

### Issue: "Unclosed client session"
**Fix:** Upgrade to v0.2.0 (fixed in dev console)

### Issue: Meta-tools not visible in dev console
**Fix:** Upgrade to v0.2.0 (now registered properly)

### Issue: Tools not loading in lazy mode
**Check logs:**
```
🔄 Lazy-loading tool 'tool_name' from 'module_path'
✅ Tool 'tool_name' loaded successfully
```

If missing, verify your server is running v0.2.0 or later.

---

## More Documentation

- **Full README:** [README.md](README.md)
- **Lazy Loading Guide:** [docs/LAZY_TOOL_LOADING.md](docs/LAZY_TOOL_LOADING.md)
- **Context Optimization:** [CONTEXT_OPTIMIZATION_SUMMARY.md](CONTEXT_OPTIMIZATION_SUMMARY.md)
- **Testing Guide:** [TESTING_GUIDE.md](TESTING_GUIDE.md)

---

## Support

- **Issues:** https://github.com/sirkirby/unifi-network-mcp/issues
- **Discussions:** https://github.com/sirkirby/unifi-network-mcp/discussions

---

**Enjoy 96% token savings with lazy mode!** 🎉
