# Build Scripts

## generate_tool_manifest.py

Generates a static tool manifest (`src/tools_manifest.json`) for lazy loading mode.

### Purpose

In lazy mode, only 3 meta-tools are registered with MCP initially. To allow LLMs to discover all available tools without loading them, we generate a static manifest at build time that lists all tools with their **complete schemas** including parameter definitions.

### Usage

```bash
# Generate manifest manually
uv run python scripts/generate_tool_manifest.py

# Or during package build (automatic)
python -m build
```

### How It Works

1. Forces eager mode to load all tools and populate TOOL_REGISTRY
2. Imports main.py to trigger the permissioned_tool decorator monkey-patch
3. Calls auto_load_tools() to execute all @server.tool decorators
4. Extracts full schemas with parameter definitions from TOOL_REGISTRY
5. Generates a JSON manifest with complete tool metadata
6. Writes to `src/tools_manifest.json`
7. At runtime, `unifi_tool_index` reads this file in lazy mode

### Output

```json
{
  "count": 64,
  "generated_by": "scripts/generate_tool_manifest.py",
  "note": "Auto-generated with full schemas from tool decorators. Do not edit manually.",
  "tools": [
    {
      "name": "unifi_list_clients",
      "description": "List clients/devices connected to the Unifi Network",
      "schema": {
        "input": {
          "type": "object",
          "properties": {
            "filter_type": {"type": "string"},
            "include_offline": {"type": "boolean"},
            "limit": {"type": "integer"}
          }
        }
      }
    },
    ...
  ]
}
```

### When to Run

- **During development:** After adding new tools to `TOOL_MODULE_MAP`
- **Before release:** To ensure manifest is up-to-date
- **In CI/CD:** As part of package build process

### Implementation Details

**Full schema extraction** is now implemented (v0.2.0):
1. ✅ Forces eager mode during build via environment variable
2. ✅ Imports main.py to trigger permissioned_tool decorator setup
3. ✅ Runs auto_load_tools() to execute all @server.tool decorators
4. ✅ Extracts complete input/output schemas from TOOL_REGISTRY
5. ✅ Includes full parameter type information in manifest

This provides LLMs with complete parameter definitions for optimal tool calling!
