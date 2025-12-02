"""Background job management for long-running UniFi operations.

This module provides an in-memory job store for tracking asynchronous operations
like device upgrades, bulk configuration changes, and other long-running tasks.

Example:
    job_id = await JOBS.start(some_async_operation())
    status = await JOBS.status(job_id)
"""

import asyncio
import logging
import secrets
import time
from typing import Any, Callable, Coroutine, Dict

logger = logging.getLogger(__name__)


class JobStore:
    """In-memory store for tracking background job states.

    Manages the lifecycle of asynchronous jobs including starting, tracking,
    and retrieving status. Jobs are stored with their state, start time,
    and eventual results or errors.

    Attributes:
        _jobs: Dictionary mapping job IDs to job state dictionaries
        _lock: Asyncio lock for thread-safe access to the job store
    """

    def __init__(self) -> None:
        """Initialize an empty job store with a lock for concurrent access."""
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def start(self, coro: Coroutine[Any, Any, Any]) -> str:
        """Start a background job and return its unique identifier.

        Creates a new job entry with a unique ID, initializes its state to 'running',
        and launches the coroutine in a background task. The task automatically
        updates the job state to 'done' or 'error' upon completion.

        Args:
            coro: The coroutine to execute as a background job

        Returns:
            A unique job identifier (16-character hex string)

        Example:
            job_id = await job_store.start(upgrade_device(mac_address))
        """
        job_id = secrets.token_hex(8)

        async with self._lock:
            self._jobs[job_id] = {
                "status": "running",
                "started": time.time(),
                "result": None,
                "error": None,
            }

        logger.info(f"Starting background job {job_id}")

        async def _runner() -> None:
            """Internal runner that executes the coroutine and updates job state."""
            try:
                result = await coro
                async with self._lock:
                    if job_id in self._jobs:
                        self._jobs[job_id]["status"] = "done"
                        self._jobs[job_id]["result"] = result
                        self._jobs[job_id]["completed"] = time.time()
                logger.info(f"Background job {job_id} completed successfully")
            except Exception as e:
                async with self._lock:
                    if job_id in self._jobs:
                        self._jobs[job_id]["status"] = "error"
                        self._jobs[job_id]["error"] = str(e)
                        self._jobs[job_id]["completed"] = time.time()
                logger.error(f"Background job {job_id} failed with error: {e}", exc_info=True)

        # Launch the runner as a background task
        asyncio.create_task(_runner())

        return job_id

    async def status(self, job_id: str) -> Dict[str, Any]:
        """Retrieve the current status of a job.

        Args:
            job_id: The unique identifier of the job to query

        Returns:
            A dictionary containing the job's state including:
            - status: 'running', 'done', 'error', or 'unknown'
            - started: Unix timestamp when the job started (if known)
            - completed: Unix timestamp when the job finished (if completed)
            - result: The return value of the job (if completed successfully)
            - error: Error message (if failed)

        Example:
            status = await job_store.status("abc123def456")
            if status["status"] == "done":
                print(status["result"])
        """
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Status requested for unknown job ID: {job_id}")
                return {"status": "unknown"}

            # Return a copy to prevent external modifications
            return dict(self._jobs[job_id])


# Global singleton instance
JOBS = JobStore()


async def start_async_tool(
    handler: Callable[..., Coroutine[Any, Any, Dict[str, Any]]], args: Dict[str, Any]
) -> Dict[str, Any]:
    """Start a tool handler as a background job.

    Wraps a tool handler function in a background job and returns the job ID
    for later status checking. This allows long-running operations to be
    executed asynchronously without blocking the MCP server.

    Args:
        handler: The async function to execute (typically a tool handler)
        args: Dictionary of arguments to pass to the handler

    Returns:
        A dictionary containing the job ID: {"jobId": "abc123def456"}

    Example:
        result = await start_async_tool(upgrade_device, {"mac_address": "..."})
        job_id = result["jobId"]
    """
    try:
        # Create a coroutine by calling the handler with unpacked args
        coro = handler(**args)
        job_id = await JOBS.start(coro)
        logger.info(f"Started async tool job {job_id} with handler {handler.__name__}")
        return {"jobId": job_id}
    except Exception as e:
        logger.error(f"Failed to start async tool: {e}", exc_info=True)
        return {"error": f"Failed to start async tool: {e}"}


async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Retrieve the status of a background job.

    A convenience wrapper around JobStore.status() for easier access
    in tool handlers.

    Args:
        job_id: The unique identifier of the job to query

    Returns:
        A dictionary containing the job's current state

    Example:
        status = await get_job_status("abc123def456")
        if status["status"] == "done":
            print("Job completed:", status["result"])
    """
    return await JOBS.status(job_id)
