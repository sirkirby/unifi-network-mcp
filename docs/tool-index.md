# Tool Index System

The UniFi Network MCP server includes a tool index and registry system that enables programmatic tool discovery and code generation.

## Overview

The tool index system captures metadata about all registered MCP tools, making it available through the `unifi_tool_index` tool. This enables:

- Code-execution mode where LLMs can discover and use tools programmatically
- Wrapper creation for client libraries
- Dynamic tool documentation
- Schema validation

## Architecture

### Components

1. **`src/tool_index.py`** - Core registry module
   - `ToolMetadata`: Dataclass storing tool metadata
   - `TOOL_REGISTRY`: Global dictionary mapping tool names to metadata
   - `register_tool()`: Function to add tools to the registry
   - `get_tool_index()`: Returns complete tool index in machine-readable format
   - `tool_index_handler()`: Async MCP tool handler for querying the index

2. **`src/runtime.py`** - Runtime access
   - `get_tool_registry()`: Cached accessor for the tool registry
   - `tool_registry`: Module-level alias for convenient access

3. **`src/main.py`** - Integration
   - Modified `permissioned_tool()` decorator to capture metadata during registration
   - Automatic input schema inference from function type annotations
   - Registration of the `unifi_tool_index` tool itself

## Usage

### Querying Available Tools

Use the `unifi_tool_index` tool to get a machine-readable list of all available tools:

```json
{
  "name": "unifi_tool_index",
  "arguments": {}
}
```

Returns:
```json
{
  "tools": [
    {
      "name": "tool_name",
      "description": "Tool description",
      "schema": {
        "input": {
          "type": "object",
          "properties": {...},
          "required": [...]
        },
        "output": {
          "type": "object",
          "properties": {...}
        }
      }
    }
  ],
  "count": 42
}
```

### Programmatic Access

```python
from src.runtime import tool_registry
from src.tool_index import get_tool_index

# Access the registry directly
all_tools = tool_registry

# Get formatted index
index = get_tool_index()
print(f"Found {index['count']} tools")
```

## Metadata Captured

For each tool, the system captures:

- **name**: Tool identifier (e.g., "unifi_list_clients")
- **description**: Human-readable description
- **input_schema**: JSON Schema describing input parameters
  - Automatically inferred from function type annotations
  - Can be explicitly provided via decorator
- **output_schema**: Optional JSON Schema for output structure
  - Must be explicitly provided via decorator

## Schema Inference

The system automatically infers input schemas from Python function signatures:

```python
@server.tool(
    name="example_tool",
    description="Example tool"
)
async def example_tool(
    filter: str,           # Required string parameter
    limit: int = 100,      # Optional integer parameter
    include_details: bool = False  # Optional boolean parameter
) -> dict:
    ...
```

Inferred schema:
```json
{
  "type": "object",
  "properties": {
    "filter": {"type": "string"},
    "limit": {"type": "integer"},
    "include_details": {"type": "boolean"}
  },
  "required": ["filter"]
}
```

Supported type mappings:
- `str` → `"string"`
- `int` → `"integer"`
- `bool` → `"boolean"`
- `float` → `"number"`
- `list` → `"array"`
- `dict` → `"object"`

## Implementation Notes

1. **Registration timing**: Tools are registered during decorator execution, which happens when tool modules are imported via `auto_load_tools()`

2. **Permission integration**: Only tools that pass permission checks are registered in both the MCP server and the tool index

3. **Logging**: Tool registrations are logged at DEBUG level for troubleshooting

4. **Error handling**: Schema inference failures gracefully fall back to empty object schema

5. **Self-registration**: The `unifi_tool_index` tool registers itself after all other tools are loaded

## Future Enhancements

Potential improvements for the tool index system:

- Enhanced type inference for complex types (List[str], Dict[str, Any], etc.)
- Support for JSON Schema validation of tool outputs
- OpenAPI/Swagger export for REST API wrapping
- Runtime schema validation for tool inputs
- Tool versioning and compatibility tracking
- Performance metrics per tool
