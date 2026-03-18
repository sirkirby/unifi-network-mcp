"""Shared permissioned_tool decorator factory for MCP servers.

Creates a decorator that gates tool registration on permission checks
and captures tool metadata for the tool index.

Example::

    from unifi_mcp_shared.permissioned_tool import create_permissioned_tool

    permissioned_tool = create_permissioned_tool(
        original_tool_decorator=_original_tool_decorator,
        permission_checker=permission_checker,
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
from typing import Annotated, Any, Callable, Union, get_args, get_origin


def create_permissioned_tool(
    *,
    original_tool_decorator: Callable,
    permission_checker: Any,
    register_tool_fn: Callable,
    diagnostics_enabled_fn: Callable[[], bool],
    wrap_tool_fn: Callable,
    logger: Any,
) -> Callable:
    """Create a permissioned_tool decorator for a specific MCP server.

    Args:
        original_tool_decorator: The original FastMCP ``server.tool`` decorator.
        permission_checker: A ``PermissionChecker`` instance for this server.
        register_tool_fn: Function to register tool metadata in the tool index.
        diagnostics_enabled_fn: Callable returning whether diagnostics are enabled.
        wrap_tool_fn: Function to wrap a tool with diagnostics logging.
        logger: Logger instance for permission messages.

    Returns:
        A ``permissioned_tool`` decorator function that acts like ``@server.tool``.
    """

    def permissioned_tool(*d_args, **d_kwargs):
        """Decorator that only registers the tool if permission allows."""

        tool_name = d_kwargs.get("name") if d_kwargs.get("name") else (d_args[0] if d_args else None)

        category = d_kwargs.pop("permission_category", None)
        action = d_kwargs.pop("permission_action", None)
        auth_method = d_kwargs.pop("auth", None)

        # Default to local_only when auth is not specified (backward compatible)
        resolved_auth = auth_method if auth_method else "local_only"

        def decorator(func):
            """Inner decorator actually registering the tool if allowed."""
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
            )

            # Check permissions for MCP server registration
            try:
                allowed = permission_checker.check(category, action)
            except Exception as exc:
                logger.error("Permission check failed for tool %s: %s", tool_name, exc)
                allowed = False

            if allowed:
                wrapped = (
                    wrap_tool_fn(func, tool_name or getattr(func, "__name__", "<tool>"))
                    if diagnostics_enabled_fn()
                    else func
                )
                return original_tool_decorator(*d_args, **d_kwargs)(wrapped)

            # Permission denied - tool is in index but not callable via MCP
            logger.info(
                "[permissions] Skipping MCP registration of tool '%s' (category=%s, action=%s)",
                tool_name,
                category,
                action,
            )
            return func

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
