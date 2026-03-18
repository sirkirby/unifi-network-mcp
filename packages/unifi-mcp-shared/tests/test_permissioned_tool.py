"""Tests for the shared permissioned_tool factory."""

import logging
from unittest.mock import MagicMock

import pytest

from unifi_mcp_shared.permissioned_tool import _infer_input_schema, create_permissioned_tool


@pytest.fixture
def mock_deps():
    """Create mock dependencies for the factory."""
    registered_tools = {}

    def fake_register(name, description="", input_schema=None, output_schema=None, auth_method="local_only"):
        registered_tools[name] = {
            "description": description,
            "input_schema": input_schema,
            "auth_method": auth_method,
        }

    def fake_tool_decorator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    checker = MagicMock()
    checker.check = MagicMock(return_value=True)

    return {
        "original_tool_decorator": fake_tool_decorator,
        "permission_checker": checker,
        "register_tool_fn": fake_register,
        "diagnostics_enabled_fn": lambda: False,
        "wrap_tool_fn": lambda func, name: func,
        "logger": logging.getLogger("test"),
        "registered_tools": registered_tools,
    }


class TestCreatePermissionedTool:
    """Tests for create_permissioned_tool factory."""

    def test_registers_tool_without_permissions(self, mock_deps):
        pt = create_permissioned_tool(
            original_tool_decorator=mock_deps["original_tool_decorator"],
            permission_checker=mock_deps["permission_checker"],
            register_tool_fn=mock_deps["register_tool_fn"],
            diagnostics_enabled_fn=mock_deps["diagnostics_enabled_fn"],
            wrap_tool_fn=mock_deps["wrap_tool_fn"],
            logger=mock_deps["logger"],
        )

        @pt(name="test_tool", description="A test")
        async def test_tool():
            return {"success": True}

        assert "test_tool" in mock_deps["registered_tools"]

    def test_registers_tool_with_permission_allowed(self, mock_deps):
        mock_deps["permission_checker"].check.return_value = True
        pt = create_permissioned_tool(
            original_tool_decorator=mock_deps["original_tool_decorator"],
            permission_checker=mock_deps["permission_checker"],
            register_tool_fn=mock_deps["register_tool_fn"],
            diagnostics_enabled_fn=mock_deps["diagnostics_enabled_fn"],
            wrap_tool_fn=mock_deps["wrap_tool_fn"],
            logger=mock_deps["logger"],
        )

        @pt(name="perm_tool", description="test", permission_category="cat", permission_action="read")
        async def perm_tool():
            return {"success": True}

        assert "perm_tool" in mock_deps["registered_tools"]
        mock_deps["permission_checker"].check.assert_called_with("cat", "read")

    def test_registers_in_index_but_skips_mcp_when_denied(self, mock_deps):
        mock_deps["permission_checker"].check.return_value = False
        pt = create_permissioned_tool(
            original_tool_decorator=mock_deps["original_tool_decorator"],
            permission_checker=mock_deps["permission_checker"],
            register_tool_fn=mock_deps["register_tool_fn"],
            diagnostics_enabled_fn=mock_deps["diagnostics_enabled_fn"],
            wrap_tool_fn=mock_deps["wrap_tool_fn"],
            logger=mock_deps["logger"],
        )

        @pt(name="denied_tool", description="test", permission_category="cat", permission_action="delete")
        async def denied_tool():
            return {"success": True}

        # Still registered in index
        assert "denied_tool" in mock_deps["registered_tools"]
        # Returns the raw function (not wrapped by tool decorator)
        # The function itself is returned unmodified

    def test_uses_function_name_when_no_name_given(self, mock_deps):
        pt = create_permissioned_tool(
            original_tool_decorator=mock_deps["original_tool_decorator"],
            permission_checker=mock_deps["permission_checker"],
            register_tool_fn=mock_deps["register_tool_fn"],
            diagnostics_enabled_fn=mock_deps["diagnostics_enabled_fn"],
            wrap_tool_fn=mock_deps["wrap_tool_fn"],
            logger=mock_deps["logger"],
        )

        @pt(description="test")
        async def my_auto_named_tool():
            return {}

        assert "my_auto_named_tool" in mock_deps["registered_tools"]


class TestInferInputSchema:
    """Tests for _infer_input_schema."""

    def test_infers_string_param(self):
        async def tool(name: str):
            pass

        schema = _infer_input_schema(tool, "tool", logging.getLogger("test"))
        assert schema["properties"]["name"]["type"] == "string"
        assert "name" in schema.get("required", [])

    def test_infers_int_param(self):
        async def tool(count: int):
            pass

        schema = _infer_input_schema(tool, "tool", logging.getLogger("test"))
        assert schema["properties"]["count"]["type"] == "integer"

    def test_infers_bool_param(self):
        async def tool(flag: bool = False):
            pass

        schema = _infer_input_schema(tool, "tool", logging.getLogger("test"))
        assert schema["properties"]["flag"]["type"] == "boolean"
        assert "flag" not in schema.get("required", [])

    def test_infers_optional_param(self):
        async def tool(name: str | None = None):
            pass

        schema = _infer_input_schema(tool, "tool", logging.getLogger("test"))
        assert schema["properties"]["name"]["type"] == "string"
        assert "name" not in schema.get("required", [])

    def test_skips_self_and_cls(self):
        async def tool(self, name: str):
            pass

        schema = _infer_input_schema(tool, "tool", logging.getLogger("test"))
        assert "self" not in schema["properties"]
