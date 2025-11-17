"""Meta-tools registration helper.

Provides a unified way to register meta-tools (tool_index, async jobs)
that work in both MCP server mode and dev console mode.
"""

import logging
from typing import Callable

logger = logging.getLogger("unifi-network-mcp")


def register_meta_tools(
    server,
    tool_decorator: Callable,
    tool_index_handler: Callable,
    start_async_tool: Callable,
    get_job_status: Callable,
    register_tool: Callable,
) -> None:
    """Register meta-tools (tool index and async jobs) with the MCP server.

    This function is used by both main.py (MCP server) and dev_console.py
    to ensure meta-tools are available in both contexts.

    Args:
        server: FastMCP server instance (for call_tool access)
        tool_decorator: The decorator function to register tools (@server.tool)
        tool_index_handler: Handler function for tool_index
        start_async_tool: Function to start async jobs
        get_job_status: Function to get job status
        register_tool: Function to register in tool index
    """

    # Register the tool index tool
    @tool_decorator(
        name="unifi_tool_index",
        description="""🔍 TOOL DISCOVERY - Use this FIRST to discover available UniFi tools when needed.

Returns a complete, machine-readable list of all 64+ UniFi network management tools including:
- Tool names and descriptions
- Input/output schemas
- Categorized by function (clients, devices, networks, firewall, VPN, QoS, etc.)

⚡ PERFORMANCE: This tool enables efficient, on-demand tool discovery. When the user asks about
UniFi capabilities or needs a specific operation, call this to find the right tool instead of
having all 64+ tools loaded in context (saves ~4,800 tokens).

WHEN TO USE:
- User asks "what can you do with UniFi?"
- Need to find tools for a specific task (e.g., "manage wireless clients")
- Building automation scripts that need tool schemas
- Generating SDK/wrapper code

Returns: JSON with tools array, count, and optional categorization""",
    )
    async def _tool_index_wrapper(args: dict | None = None) -> dict:
        """Wrapper for the tool index handler."""
        return await tool_index_handler(args)

    # Register it in the tool index as well
    register_tool(
        name="unifi_tool_index",
        description="Returns machine-readable list of available UniFi MCP tools with their schemas for code generation and wrapper creation",
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "input": {"type": "object"},
                                    "output": {"type": "object"},
                                },
                            },
                        },
                    },
                },
                "count": {"type": "integer"},
            },
        },
    )

    # Register async start tool
    @tool_decorator(
        name="unifi_async_start",
        description="Start a background job for a long-running UniFi operation. Returns a job ID to check status.",
    )
    async def async_start_handler(tool: str, arguments: dict = None) -> dict:
        """Start a background job for a long-running tool execution.

        Args:
            tool: Name of the tool to execute (e.g., "unifi_upgrade_device")
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Dictionary with "jobId" key containing the unique job identifier

        Example:
            {"tool": "unifi_upgrade_device", "arguments": {"mac_address": "aa:bb:cc:dd:ee:ff", "confirm": true}}
        """
        if arguments is None:
            arguments = {}

        try:
            # Use server.call_tool to invoke the tool and wrap it in a job
            async def _execute_tool():
                return await server.call_tool(tool, arguments)

            job_id = await start_async_tool(_execute_tool, {})
            return job_id
        except Exception as e:
            logger.error(f"Error starting async tool '{tool}': {e}", exc_info=True)
            return {"error": f"Failed to start async tool: {str(e)}"}

    # Register async status tool
    @tool_decorator(
        name="unifi_async_status",
        description="Check the status of a background job. Returns status, result (if done), or error (if failed).",
    )
    async def async_status_handler(jobId: str) -> dict:
        """Check the status of a background job.

        Args:
            jobId: Job ID returned from unifi_async_start

        Returns:
            Dictionary with job status including:
            - status: "running", "done", "error", or "unknown"
            - started: Unix timestamp when job started (if known)
            - completed: Unix timestamp when job completed (if finished)
            - result: Result of the job (if completed successfully)
            - error: Error message (if failed)

        Example:
            {"jobId": "abc123def456"}
        """
        try:
            status = await get_job_status(jobId)
            return status
        except Exception as e:
            logger.error(f"Error getting job status for '{jobId}': {e}", exc_info=True)
            return {"status": "error", "error": f"Failed to get job status: {str(e)}"}

    # Register async tools in the tool index
    register_tool(
        name="unifi_async_start",
        description="Start a background job for a long-running UniFi operation. Returns a job ID to check status.",
        input_schema={
            "type": "object",
            "required": ["tool"],
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "Name of the tool to execute",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the tool",
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "jobId": {"type": "string", "description": "Unique job identifier"}
            },
        },
    )

    register_tool(
        name="unifi_async_status",
        description="Check the status of a background job. Returns status, result (if done), or error (if failed).",
        input_schema={
            "type": "object",
            "required": ["jobId"],
            "properties": {
                "jobId": {
                    "type": "string",
                    "description": "Job ID returned from async_start",
                }
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["running", "done", "error", "unknown"],
                    "description": "Current job status",
                },
                "started": {
                    "type": "number",
                    "description": "Unix timestamp when job started",
                },
                "completed": {
                    "type": "number",
                    "description": "Unix timestamp when job completed",
                },
                "result": {"description": "Result of the job (if completed)"},
                "error": {"type": "string", "description": "Error message (if failed)"},
            },
        },
    )

    logger.info(
        "Registered meta-tools: unifi_tool_index, unifi_async_start, unifi_async_status"
    )
