#!/usr/bin/env python3
"""Example: Using async jobs for long-running operations.

This demonstrates how to start background jobs and check their status,
useful for operations like device upgrades or bulk configuration changes.

Usage:
    python examples/python/use_async_jobs.py
"""

import asyncio
import json
import time
from typing import Any, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def start_async_job(
    session: ClientSession,
    tool_name: str,
    arguments: Dict[str, Any]
) -> str:
    """Start an async job and return the job ID."""
    result = await session.call_tool(
        "unifi_async_start",
        arguments={
            "tool": tool_name,
            "arguments": arguments
        }
    )

    # Extract job ID from result
    content = result.content[0].text if hasattr(result, 'content') else result
    if isinstance(content, str):
        content = json.loads(content)

    return content["jobId"]


async def check_job_status(session: ClientSession, job_id: str) -> Dict[str, Any]:
    """Check the status of an async job."""
    result = await session.call_tool(
        "unifi_async_status",
        arguments={"jobId": job_id}
    )

    # Extract status from result
    content = result.content[0].text if hasattr(result, 'content') else result
    if isinstance(content, str):
        content = json.loads(content)

    return content


async def wait_for_job(
    session: ClientSession,
    job_id: str,
    timeout: int = 60,
    poll_interval: float = 1.0
) -> Dict[str, Any]:
    """Wait for a job to complete, polling periodically."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = await check_job_status(session, job_id)

        if status["status"] in ["done", "error"]:
            return status

        await asyncio.sleep(poll_interval)

    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


async def main():
    """Main function demonstrating async job usage."""
    print("=" * 70)
    print("UniFi Network MCP - Async Jobs Example")
    print("=" * 70)
    print()

    server_params = StdioServerParameters(
        command="unifi-network-mcp",
        args=["--stdio"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Example 1: Start a simple read-only job
            print("Example 1: Async job with read-only operation")
            print("-" * 70)

            try:
                # Start a job to list clients (simulating a slow operation)
                print("Starting async job: unifi_list_clients...")
                job_id = await start_async_job(
                    session,
                    "unifi_list_clients",
                    {"limit": 10}
                )
                print(f"✓ Job started: {job_id}")
                print()

                # Poll for status
                print("Polling job status...")
                for i in range(5):
                    await asyncio.sleep(0.5)
                    status = await check_job_status(session, job_id)
                    print(f"  [{i+1}] Status: {status['status']}")

                    if status["status"] == "done":
                        print()
                        print("✓ Job completed successfully!")
                        print(f"  Result preview: {str(status.get('result', {}))[:100]}...")
                        break
                    elif status["status"] == "error":
                        print()
                        print(f"✗ Job failed: {status.get('error')}")
                        break

            except Exception as e:
                print(f"✗ Error: {e}")

            print()
            print()

            # Example 2: Check status of unknown job
            print("Example 2: Checking unknown job ID")
            print("-" * 70)

            try:
                fake_job_id = "nonexistent_job_id"
                print(f"Checking status of: {fake_job_id}...")
                status = await check_job_status(session, fake_job_id)
                print(f"Status: {status['status']}")

            except Exception as e:
                print(f"Expected behavior - job not found: {status}")

            print()
            print()

            # Example 3: Demonstrate the full workflow
            print("Example 3: Complete async workflow")
            print("-" * 70)
            print("""
This example shows how you would use async jobs for real long-running
operations like:

  • Device firmware upgrades (unifi_upgrade_device)
  • Bulk client operations (block/unblock multiple clients)
  • Large data exports (historical statistics)
  • Network-wide configuration changes

Workflow:
  1. Start job with unifi_async_start
  2. Save the job ID
  3. Poll with unifi_async_status until done
  4. Process the result or handle errors

Benefits:
  • Non-blocking - continue other work while job runs
  • Progress tracking - check status anytime
  • Error handling - jobs capture exceptions
  • Timeout control - set your own timeout limits
            """)

            print("=" * 70)
            print("✓ Examples complete!")
            print()
            print("Next steps:")
            print("  • Try with a real long-running operation")
            print("  • Implement progress bars using job status")
            print("  • Build a job queue for batch operations")
            print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
