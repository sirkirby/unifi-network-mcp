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
        return False

    # Display detection result
    if hasattr(connection_manager, '_unifi_os_override'):
        if connection_manager._unifi_os_override is True:
            print("✓ Controller Type: UniFi OS (proxy paths)")
        elif connection_manager._unifi_os_override is False:
            print("✓ Controller Type: Standard (direct paths)")
        else:
            print("⚠ Controller Type: Using aiounifi auto-detection")

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


def _coerce_value(val: str, schema: Optional[Dict[str, Any]]) -> Any:
    if schema is None:
        return val
    t = schema.get("type") if isinstance(schema, dict) else None
    if val == "" and schema.get("default") is not None:
        return schema["default"]
    if t == "boolean":
        return val.strip().lower() in {"1", "true", "yes", "on"}
    if t == "integer":
        try:
            return int(val)
        except Exception:
            return val
    if t == "number":
        try:
            return float(val)
        except Exception:
            return val
    if t in {"array", "object"}:
        # allow JSON input for complex types
        try:
            parsed = json.loads(val)
            return parsed
        except Exception:
            return val
    return val


def _parse_args_with_schema(params_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    print("Enter JSON arguments (single line). Press Enter for guided prompts.")
    hint = None
    if params_schema and isinstance(params_schema, dict):
        hint = {
            "properties": params_schema.get("properties", {}),
            "required": params_schema.get("required", []),
        }
    if hint:
        try:
            print("Hint (not validated):")
            print(json.dumps(hint, indent=2, ensure_ascii=False, default=str))
        except Exception:
            pass
    line = input("> ").strip()

    # If user pasted JSON, parse directly
    if line.startswith("{") or line.startswith("["):
        try:
            data = json.loads(line)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.error(f"Invalid JSON: {exc}. Proceeding to guided prompts.")

    # If non-empty and single required param, treat as simple value
    if line and params_schema:
        req = params_schema.get("required", []) or []
        props = params_schema.get("properties", {}) or {}
        if isinstance(req, list) and len(req) == 1 and isinstance(props, dict) and req[0] in props:
            only_key = req[0]
            coerced = _coerce_value(line, props.get(only_key))
            return {only_key: coerced}

    # Guided prompts for required fields
    args: Dict[str, Any] = {}
    if params_schema and isinstance(params_schema, dict):
        props = params_schema.get("properties", {}) or {}
        required = params_schema.get("required", []) or []
        for key in required:
            sch = props.get(key) if isinstance(props, dict) else None
            default = sch.get("default") if isinstance(sch, dict) else None
            val = _prompt(f"{key}", str(default) if default is not None else None)
            args[key] = _coerce_value(val, sch)
        # Optionally allow optional properties quickly
        # If user wants to add more, they can paste JSON on next run
        return args

    # No schema: if user typed nothing, return empty; if something non-JSON, ask as key=value JSON next time
    return {}


async def _invoke_tool(server, tool) -> None:
    name = tool.name
    desc = tool.description or ""
    params = getattr(tool, "parameters", None)
    _print("Tool", {"name": name, "description": desc})

    args: Dict[str, Any] = {}
    args = _parse_args_with_schema(params if isinstance(params, dict) else None)

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

    def _extract_missing_fields_from_exc(e: Exception) -> List[str]:
        txt = str(e)
        fields: List[str] = []
        try:
            lines = txt.splitlines()
            for i, ln in enumerate(lines):
                s = ln.strip()
                # Heuristic: a bare identifier line followed by a 'Field required' line
                if s and s.replace("_", "").isalnum() and " " not in s:
                    if i + 1 < len(lines) and "Field required" in lines[i + 1]:
                        fields.append(s)
        except Exception:
            pass
        return fields

    try:
        result = await server.call_tool(name, args)
        _print("Result", result)
    except Exception as exc:
        # If we had no args and no schema, try to guide based on validation error
        if not args and not (isinstance(params, dict) and params.get("properties")):
            missing = _extract_missing_fields_from_exc(exc)
            if missing:
                logger.info(f"Missing required fields: {missing}")
                fixed: Dict[str, Any] = {}
                for key in missing:
                    val = _prompt(key)
                    fixed[key] = val
                _print("Re-invoking", {"tool": name, "args": fixed})
                try:
                    result = await server.call_tool(name, fixed)
                    _print("Result", result)
                    return
                except Exception as exc2:
                    logger.error(f"Tool execution failed after prompting: {exc2}")
                    return
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


