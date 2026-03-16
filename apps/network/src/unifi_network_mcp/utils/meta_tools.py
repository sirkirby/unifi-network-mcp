"""Meta-tools registration helper.

Provides a unified way to register meta-tools (tool_index, execute, batch, job_status)
that work in both MCP server mode and dev console mode.
"""

import logging
from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from src.utils.lazy_tool_loader import LazyToolLoader

logger = logging.getLogger("unifi-network-mcp")


def register_meta_tools(
    server,
    tool_decorator: Callable,
    tool_index_handler: Callable,
    start_async_tool: Callable,
    get_job_status: Callable,
    register_tool: Callable,
) -> None:
    """Register meta-tools with the MCP server.

    Tools registered:
    - unifi_tool_index: Discover available tools
    - unifi_execute: Execute a single tool (returns result directly)
    - unifi_batch: Execute multiple tools in parallel (returns job IDs)
    - unifi_batch_status: Check batch job progress

    Args:
        server: FastMCP server instance (for call_tool access)
        tool_decorator: The decorator function to register tools (@server.tool)
        tool_index_handler: Handler function for tool_index
        start_async_tool: Function to start async jobs
        get_job_status: Function to get job status
        register_tool: Function to register in tool index
    """

    # =========================================================================
    # DISCOVERY: unifi_tool_index
    # =========================================================================
    @tool_decorator(
        name="unifi_tool_index",
        description="""List all 80+ available UniFi tools and their schemas.

CALL THIS FIRST to discover the right tool for your task.
Tools are organized by category: clients, devices, networks, firewall, VPN, stats, etc.

After finding the right tool, use unifi_execute to run it.""",
    )
    async def _tool_index_wrapper(args: dict | None = None) -> dict:
        return await tool_index_handler(args)

    register_tool(
        name="unifi_tool_index",
        description="CALL FIRST - List all 80+ UniFi tools with schemas to find the right one for your task.",
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {
                "tools": {"type": "array", "description": "Available tools with schemas"},
                "count": {"type": "integer"},
            },
        },
    )

    # =========================================================================
    # SINGLE EXECUTION: unifi_execute
    # =========================================================================
    @tool_decorator(
        name="unifi_execute",
        description="""Execute a UniFi tool discovered via unifi_tool_index.

WORKFLOW: Call unifi_tool_index first to find the right tool, then execute it here.

PARAMETERS:
- tool: Tool name from unifi_tool_index
- arguments: Tool parameters (see tool schema from unifi_tool_index)

For bulk/parallel operations, use unifi_batch instead.""",
    )
    async def execute_handler(tool: str, arguments: dict = None) -> dict:
        """Execute a UniFi tool synchronously."""
        if arguments is None:
            arguments = {}

        try:
            result = await server.call_tool(tool, arguments)
            return result
        except Exception as e:
            logger.error(f"Error executing tool '{tool}': {e}", exc_info=True)
            return {"error": f"Failed to execute tool: {str(e)}"}

    register_tool(
        name="unifi_execute",
        description="Execute a tool discovered via unifi_tool_index. Call unifi_tool_index first.",
        input_schema={
            "type": "object",
            "required": ["tool"],
            "properties": {
                "tool": {"type": "string", "description": "Tool name from unifi_tool_index"},
                "arguments": {"type": "object", "description": "Tool parameters from schema"},
            },
        },
        output_schema={"type": "object", "description": "Tool result"},
    )

    # =========================================================================
    # BATCH EXECUTION: unifi_batch
    # =========================================================================
    @tool_decorator(
        name="unifi_batch",
        description="""Execute multiple UniFi tools in parallel.

WORKFLOW: Call unifi_tool_index first to discover tools, then batch execute them here.

Returns job IDs for each operation. Use unifi_batch_status to check progress and get results.

PARAMETERS:
- operations: Array of {tool, arguments} objects where tool names come from unifi_tool_index

USE FOR: Bulk operations, parallel execution, long-running tasks.
FOR SINGLE OPERATIONS: Use unifi_execute instead (returns result directly).""",
    )
    async def batch_handler(operations: List[dict]) -> dict:
        """Execute multiple operations in parallel."""
        if not operations:
            return {"error": "No operations specified", "jobs": []}

        jobs = []
        errors = []

        for i, op in enumerate(operations):
            tool = op.get("tool")
            arguments = op.get("arguments", {})

            if not tool:
                errors.append({"index": i, "error": "Missing 'tool' field"})
                continue

            try:
                # Create a closure that captures the current tool and arguments
                async def _make_executor(t, a):
                    async def _execute():
                        return await server.call_tool(t, a)

                    return _execute

                executor = await _make_executor(tool, arguments)
                job_result = await start_async_tool(executor, {})

                jobs.append(
                    {
                        "index": i,
                        "tool": tool,
                        "jobId": job_result.get("jobId"),
                    }
                )
            except Exception as e:
                logger.error(f"Error starting batch operation {i} ({tool}): {e}", exc_info=True)
                errors.append({"index": i, "tool": tool, "error": str(e)})

        return {
            "jobs": jobs,
            "errors": errors if errors else None,
            "message": f"Started {len(jobs)} operation(s). Use unifi_batch_status to check progress.",
        }

    register_tool(
        name="unifi_batch",
        description="Execute multiple tools in parallel. Returns job IDs for status checking.",
        input_schema={
            "type": "object",
            "required": ["operations"],
            "properties": {
                "operations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["tool"],
                        "properties": {
                            "tool": {"type": "string"},
                            "arguments": {"type": "object"},
                        },
                    },
                    "description": "Array of {tool, arguments} objects",
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "jobs": {"type": "array", "description": "Started jobs with IDs"},
                "errors": {"type": "array", "description": "Any errors"},
            },
        },
    )

    # =========================================================================
    # BATCH STATUS: unifi_batch_status
    # =========================================================================
    @tool_decorator(
        name="unifi_batch_status",
        description="""Check status of operations started with unifi_batch.

Returns: status ("running", "done", "error"), result (if done), error (if failed).

Can check multiple jobs at once by passing an array of job IDs.""",
    )
    async def batch_status_handler(jobId: str = None, jobIds: List[str] = None) -> dict:
        """Check status of one or more jobs."""
        # Handle single job ID
        if jobId and not jobIds:
            try:
                status = await get_job_status(jobId)
                return status
            except Exception as e:
                logger.error(f"Error getting job status for '{jobId}': {e}", exc_info=True)
                return {"status": "error", "error": str(e)}

        # Handle multiple job IDs
        if jobIds:
            results = []
            for jid in jobIds:
                try:
                    status = await get_job_status(jid)
                    results.append({"jobId": jid, **status})
                except Exception as e:
                    results.append({"jobId": jid, "status": "error", "error": str(e)})
            return {"jobs": results}

        return {"error": "Provide jobId or jobIds parameter"}

    register_tool(
        name="unifi_batch_status",
        description="Check status of batch operations. Returns status, result (if done), or error.",
        input_schema={
            "type": "object",
            "properties": {
                "jobId": {"type": "string", "description": "Single job ID to check"},
                "jobIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Multiple job IDs to check",
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["running", "done", "error", "unknown"]},
                "result": {"description": "Result (if done)"},
                "error": {"type": "string", "description": "Error message (if failed)"},
                "jobs": {"type": "array", "description": "Status of multiple jobs"},
            },
        },
    )

    logger.info("Registered meta-tools: unifi_tool_index, unifi_execute, unifi_batch, unifi_batch_status")


def register_load_tools(
    server,
    tool_decorator: Callable,
    lazy_loader: "LazyToolLoader",
    register_tool: Callable,
) -> None:
    """Register unifi_load_tools for dynamic tool loading (capable clients only).

    This enables direct tool access for MCP clients that support tool_list_changed notifications.
    Most users should use unifi_execute instead - it works with all clients.
    """
    from mcp.server.fastmcp import Context

    from src.utils.lazy_tool_loader import TOOL_MODULE_MAP

    @tool_decorator(
        name="unifi_load_tools",
        description="""Load tools for direct MCP access (advanced).

Most users should use unifi_execute instead - it works with all clients.

This tool is for MCP clients that support tool_list_changed notifications.
After loading, the client is notified to refresh its tool list.

EXAMPLE: {"tools": ["unifi_list_clients", "unifi_list_devices"]}""",
    )
    async def load_tools_handler(tools: List[str], ctx: Context) -> dict:
        """Load specific tools and notify the client."""
        if not tools:
            return {"error": "No tools specified", "loaded": [], "errors": []}

        loaded = []
        errors = []

        for tool_name in tools:
            if tool_name not in TOOL_MODULE_MAP:
                errors.append({"tool": tool_name, "error": "Unknown tool"})
                continue

            try:
                success = await lazy_loader.load_tool(tool_name)
                if success:
                    loaded.append(tool_name)
                else:
                    errors.append({"tool": tool_name, "error": "Failed to load"})
            except Exception as e:
                logger.error(f"Error loading tool '{tool_name}': {e}", exc_info=True)
                errors.append({"tool": tool_name, "error": str(e)})

        if loaded:
            try:
                await ctx.session.send_tool_list_changed()
                logger.info(f"Sent tool_list_changed notification after loading: {loaded}")
            except Exception as e:
                logger.warning(f"Failed to send tool_list_changed notification: {e}")

        return {
            "loaded": loaded,
            "errors": errors if errors else None,
            "message": f"Loaded {len(loaded)} tool(s). Client should refresh tool list.",
        }

    register_tool(
        name="unifi_load_tools",
        description="Load tools for direct MCP access (advanced). Most users should use unifi_execute.",
        input_schema={
            "type": "object",
            "required": ["tools"],
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tool names to load",
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "loaded": {"type": "array", "description": "Successfully loaded tools"},
                "errors": {"type": "array", "description": "Any errors"},
                "message": {"type": "string"},
            },
        },
    )

    logger.info("Registered unifi_load_tools meta-tool for dynamic tool loading")
