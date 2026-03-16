"""Tool index and registry system for the UniFi Network MCP server.

This module provides a registry to capture metadata about all registered tools,
enabling code-execution mode and programmatic tool discovery.

The registry is populated during tool registration via the permissioned_tool
decorator in main.py, and can be queried via the unifi_tool_index tool.

In lazy mode, tool metadata is read from a static manifest (tools_manifest.json)
generated at build time, allowing full tool discovery without runtime imports.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool metadata structure
# ---------------------------------------------------------------------------


@dataclass
class ToolMetadata:
    """Metadata about a registered MCP tool.

    Attributes:
        name: Tool name (e.g., "unifi_list_clients")
        description: Human-readable description of what the tool does
        input_schema: JSON Schema describing the tool's input parameters
        output_schema: Optional JSON Schema describing the tool's output structure
    """

    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


# ---------------------------------------------------------------------------
# Global tool registry
# ---------------------------------------------------------------------------

# Global dictionary mapping tool names to their metadata
TOOL_REGISTRY: Dict[str, ToolMetadata] = {}


def register_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any] | None = None,
    output_schema: Dict[str, Any] | None = None,
) -> None:
    """Register a tool in the global registry.

    This function is called during tool registration to capture metadata
    for later retrieval via the tool index.

    Args:
        name: Tool name
        description: Tool description
        input_schema: JSON Schema for input parameters (defaults to empty object)
        output_schema: Optional JSON Schema for output structure
    """
    if input_schema is None:
        input_schema = {"type": "object", "properties": {}}

    metadata = ToolMetadata(
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
    )

    TOOL_REGISTRY[name] = metadata
    logger.debug(f"Registered tool in index: {name}")


def get_tool_index() -> Dict[str, Any]:
    """Get the complete tool index in machine-readable format.

    In lazy loading mode, reads tool metadata from a static manifest file
    (tools_manifest.json) generated at build time. This provides full tool
    schemas without runtime imports.

    Returns:
        Dictionary with "tools" key containing list of tool metadata objects.
        Each tool includes: name, description, input_schema, and optionally output_schema.
    """
    # In lazy mode, read from static manifest
    try:
        from src.bootstrap import UNIFI_TOOL_REGISTRATION_MODE

        if UNIFI_TOOL_REGISTRATION_MODE == "lazy":
            # Try to load static manifest first
            manifest_path = Path(__file__).parent / "tools_manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    logger.debug(f"Loaded tool index from manifest: {manifest['count']} tools")
                    return manifest
                except Exception as e:
                    logger.warning(f"Failed to load tool manifest: {e}, falling back to runtime")
            else:
                logger.warning(
                    f"Tool manifest not found at {manifest_path}. "
                    "Run 'python scripts/generate_tool_manifest.py' to generate it."
                )
    except ImportError:
        # If bootstrap doesn't exist, fall through to normal mode
        pass

    # Fallback: return registered tools (for eager/meta_only or if manifest missing)
    tools = [
        {
            "name": meta.name,
            "description": meta.description,
            "schema": {
                "input": meta.input_schema,
                **({"output": meta.output_schema} if meta.output_schema else {}),
            },
        }
        for meta in TOOL_REGISTRY.values()
    ]

    return {
        "tools": tools,
        "count": len(tools),
    }


# ---------------------------------------------------------------------------
# MCP tool handler
# ---------------------------------------------------------------------------


async def tool_index_handler(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Handler for the unifi_tool_index tool.

    Returns machine-readable list of available UniFi MCP tools with their schemas
    for code generation and wrapper creation.

    Args:
        args: Optional arguments (unused, but required for MCP tool signature)

    Returns:
        Dictionary containing tool index with all registered tools and their schemas.
    """
    return get_tool_index()
