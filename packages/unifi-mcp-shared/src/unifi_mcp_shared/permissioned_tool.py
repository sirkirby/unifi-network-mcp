"""Shared permissioned_tool decorator factory for MCP servers.

Creates a decorator that always registers tools with MCP and checks
policy gates at call time (not registration time).

Example::

    from unifi_mcp_shared.permissioned_tool import create_permissioned_tool

    permissioned_tool = create_permissioned_tool(
        original_tool_decorator=_original_tool_decorator,
        policy_gate_checker=policy_gate_checker,
        server_prefix="NETWORK",
        register_tool_fn=register_tool,
        diagnostics_enabled_fn=diagnostics_enabled,
        wrap_tool_fn=wrap_tool,
        logger=logger,
    )
    server.tool = permissioned_tool
"""

from __future__ import annotations

import inspect
import types
from functools import wraps
from typing import Annotated, Any, Callable, Union, get_args, get_origin

from unifi_mcp_shared.policy_gate import resolve_permission_mode


def setup_permissioned_tool(
    *,
    server: Any,
    category_map: dict[str, str],
    server_prefix: str,
    register_tool_fn: Callable,
    diagnostics_enabled_fn: Callable[[], bool],
    wrap_tool_fn: Callable,
    logger: Any,
) -> Callable:
    """One-call setup: create a permissioned_tool decorator and install it on *server*.

    This is a convenience wrapper around :func:`create_permissioned_tool` that also
    creates the ``PolicyGateChecker`` and replaces ``server.tool``.

    Returns the permissioned_tool decorator (also installed as ``server.tool``).
    """
    from unifi_mcp_shared.policy_gate import PolicyGateChecker

    original = getattr(server, "_original_tool", server.tool)
    checker = PolicyGateChecker(server_prefix=server_prefix, category_map=category_map)
    pt = create_permissioned_tool(
        original_tool_decorator=original,
        policy_gate_checker=checker,
        server_prefix=server_prefix,
        register_tool_fn=register_tool_fn,
        diagnostics_enabled_fn=diagnostics_enabled_fn,
        wrap_tool_fn=wrap_tool_fn,
        logger=logger,
    )
    server.tool = pt  # type: ignore[assignment]
    return pt


def create_permissioned_tool(
    *,
    original_tool_decorator: Callable,
    policy_gate_checker: Any,
    server_prefix: str,
    register_tool_fn: Callable,
    diagnostics_enabled_fn: Callable[[], bool],
    wrap_tool_fn: Callable,
    logger: Any,
) -> Callable:
    """Create a permissioned_tool decorator for a specific MCP server.

    Args:
        original_tool_decorator: The original FastMCP ``server.tool`` decorator.
        policy_gate_checker: A ``PolicyGateChecker`` instance for this server.
        server_prefix: The server prefix for permission mode resolution (e.g. "NETWORK").
        register_tool_fn: Function to register tool metadata in the tool index.
        diagnostics_enabled_fn: Callable returning whether diagnostics are enabled.
        wrap_tool_fn: Function to wrap a tool with diagnostics logging.
        logger: Logger instance for permission messages.

    Returns:
        A ``permissioned_tool`` decorator function that acts like ``@server.tool``.
    """

    def permissioned_tool(*d_args, **d_kwargs):
        """Decorator that registers the tool and checks policy gates at call time."""

        tool_name = d_kwargs.get("name") if d_kwargs.get("name") else (d_args[0] if d_args else None)

        category = d_kwargs.pop("permission_category", None)
        action = d_kwargs.pop("permission_action", None)
        auth_method = d_kwargs.pop("auth", None)

        # Default to local_only when auth is not specified (backward compatible)
        resolved_auth = auth_method if auth_method else "local_only"

        def decorator(func):
            """Inner decorator that always registers the tool with MCP."""
            nonlocal category, action, tool_name

            if not tool_name:
                tool_name = getattr(func, "__name__", "<unknown>")

            description = d_kwargs.get("description", "")
            input_schema = d_kwargs.get("input_schema")
            output_schema = d_kwargs.get("output_schema")

            # If no explicit input_schema, try to infer from function annotations
            if input_schema is None:
                input_schema = _infer_input_schema(func, tool_name, logger)

            # Fast path: no permissions requested, just register.
            if not category or not action:
                register_tool_fn(
                    name=tool_name,
                    description=description,
                    input_schema=input_schema,
                    output_schema=output_schema,
                    auth_method=resolved_auth,
                )
                return original_tool_decorator(*d_args, **d_kwargs)(func)

            # ALWAYS register in tool index (for discovery)
            register_tool_fn(
                name=tool_name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
                auth_method=resolved_auth,
                permission_category=category,
                permission_action=action,
            )

            # Wrap function with policy gate + bypass injection
            @wraps(func)
            async def gated_func(*args, **kwargs):
                # 1. Policy gate check at call time
                if not policy_gate_checker.check(category, action):
                    return {"success": False, "error": policy_gate_checker.denial_message(category, action)}

                # 2. Bypass injection — only for mutation actions with confirm param
                if action.lower() != "read":
                    mode = resolve_permission_mode(server_prefix)
                    if mode == "bypass":
                        sig = inspect.signature(func)
                        if "confirm" in sig.parameters:
                            kwargs["confirm"] = True

                return await func(*args, **kwargs)

            # Apply diagnostics wrapping if enabled
            wrapped = (
                wrap_tool_fn(gated_func, tool_name or getattr(func, "__name__", "<tool>"))
                if diagnostics_enabled_fn()
                else gated_func
            )

            # ALWAYS register with MCP
            return original_tool_decorator(*d_args, **d_kwargs)(wrapped)

        return decorator

    return permissioned_tool


def _infer_input_schema(func: Callable, tool_name: str, logger: Any) -> dict[str, Any]:
    """Infer JSON Schema input_schema from function type annotations."""
    try:
        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls") or param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            param_type = "string"
            param_description = None

            if param.annotation != inspect.Parameter.empty:
                ann = param.annotation

                # Unwrap Annotated[T, Field(...)]
                if get_origin(ann) is Annotated:
                    annotated_args = get_args(ann)
                    ann = annotated_args[0] if annotated_args else ann
                    for metadata in annotated_args[1:]:
                        if hasattr(metadata, "description") and metadata.description:
                            param_description = metadata.description
                            break

                # Unwrap Optional / X | None unions
                if isinstance(ann, types.UnionType) or get_origin(ann) is Union:
                    args = get_args(ann)
                    non_none = [a for a in args if a is not types.NoneType]
                    if non_none:
                        ann = non_none[0]

                origin = get_origin(ann)
                if origin is dict or ann in (dict, "dict"):
                    param_type = "object"
                elif origin is list or ann in (list, "list"):
                    param_type = "array"
                elif ann in (int, "int"):
                    param_type = "integer"
                elif ann in (bool, "bool"):
                    param_type = "boolean"
                elif ann in (float, "float"):
                    param_type = "number"

            prop: dict[str, Any] = {"type": param_type}
            if param_description:
                prop["description"] = param_description
            properties[param_name] = prop

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    except Exception as exc:
        logger.debug("Could not infer input schema for %s: %s", tool_name, exc)
        return {"type": "object", "properties": {}}
