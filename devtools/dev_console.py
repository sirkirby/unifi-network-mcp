from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Defer heavy imports until runtime is needed to provide clearer errors
logger = None  # type: ignore


def _print(title: str = "", obj: Any = None) -> None:
    if title:
        print(f"\n=== {title} ===")
    if obj is not None:
        try:
            print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
        except Exception:
            print(str(obj))


async def _ensure_connected(connection_manager) -> bool:
    ok = await connection_manager.initialize()
    if not ok:
        logger.error("Unable to establish UniFi connection. Check your config/credentials.")
    return ok


async def _list_tools(server) -> List[Any]:
    try:
        tools = await server.list_tools()
        return tools
    except Exception as exc:
        logger.error(f"Failed to list tools: {exc}")
        return []


def _prompt(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else (default or "")


def _parse_json_input(hint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    print("Enter JSON arguments (single line). Press Enter for {}.")
    if hint:
        try:
            print("Hint (not validated):")
            print(json.dumps(hint, indent=2, ensure_ascii=False, default=str))
        except Exception:
            pass
    line = input("> ").strip()
    if not line:
        return {}
    try:
        data = json.loads(line)
        if isinstance(data, dict):
            return data
        logger.warning("Top-level JSON must be an object; ignoring input.")
        return {}
    except Exception as exc:
        logger.error(f"Invalid JSON: {exc}. Using empty args.")
        return {}


async def _invoke_tool(server, tool) -> None:
    name = tool.name
    desc = tool.description or ""
    params = getattr(tool, "parameters", None)
    _print("Tool", {"name": name, "description": desc})

    args: Dict[str, Any] = {}
    if params and isinstance(params, dict) and params.get("properties"):
        # Show properties as a hint and accept JSON dict
        args = _parse_json_input({"properties": params.get("properties", {}), "required": params.get("required", [])})
    else:
        # No schema provided; still allow raw JSON args
        args = _parse_json_input()

    confirm_default = None
    if "confirm" in (params.get("properties", {}) if isinstance(params, dict) else {}):
        confirm_default = "false"

    # Optionally prompt for confirm if applicable
    if "confirm" in args:
        pass
    elif confirm_default is not None:
        yn = _prompt("Set confirm? (true/false)", confirm_default)
        if yn.lower() in {"1", "true", "yes", "on"}:
            args["confirm"] = True
        elif yn.lower() in {"0", "false", "no", "off"}:
            args["confirm"] = False

    _print("Invoking", {"tool": name, "args": args})
    try:
        result = await server.call_tool(name, args)
        _print("Result", result)
    except Exception as exc:
        logger.error(f"Tool execution failed: {exc}")


async def main_async() -> None:
    global logger
    try:
        from src.bootstrap import logger as _logger  # noqa: E402
        logger = _logger
    except Exception:
        class _Fallback:
            def info(self, *a, **k):
                print(*a)
            def warning(self, *a, **k):
                print(*a)
            def error(self, *a, **k):
                print(*a)
        logger = _Fallback()  # type: ignore

    logger.info("Developer console starting...")

    try:
        # Import runtime lazily to provide actionable error if MCP SDK missing
        from src.runtime import server, connection_manager  # noqa: E402
        from src.utils.tool_loader import auto_load_tools  # noqa: E402
    except ModuleNotFoundError as e:
        if str(e).startswith("No module named 'mcp'"):
            print("\nERROR: Python MCP SDK not found (module 'mcp').")
            print("Fix:")
            print("  - Activate the project venv: source venv/bin/activate")
            print("  - Or install the SDK: pip install mcp  # or: uv pip install mcp")
            print("  - Then run: python devtools/dev_console.py\n")
            return
        raise

    auto_load_tools()
    if not await _ensure_connected(connection_manager):
        return

    while True:
        tools = await _list_tools(server)
        if not tools:
            print("No tools registered or accessible.")
            return

        print("\nAvailable tools:")
        for idx, t in enumerate(tools, start=1):
            print(f"  {idx:3d}. {t.name} - {t.description or ''}")
        print("  0. Exit")

        choice = _prompt("Select tool by number", "0")
        if not choice.isdigit():
            print("Enter a number.")
            continue
        num = int(choice)
        if num == 0:
            print("Goodbye.")
            return
        if 1 <= num <= len(tools):
            await _invoke_tool(server, tools[num - 1])
        else:
            print("Out of range.")


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()


