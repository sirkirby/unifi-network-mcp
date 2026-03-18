"""Tests for the shared validators module."""

import pytest

from unifi_mcp_shared.validators import ResourceValidator, create_response


class TestResourceValidator:
    """Tests for the ResourceValidator class."""

    def test_valid_params(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        validator = ResourceValidator(schema, "TestResource")
        is_valid, error, params = validator.validate({"name": "test"})
        assert is_valid is True
        assert error is None
        assert params == {"name": "test"}

    def test_invalid_params_missing_required(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        validator = ResourceValidator(schema, "TestResource")
        is_valid, error, params = validator.validate({})
        assert is_valid is False
        assert "TestResource validation error" in error
        assert params is None

    def test_invalid_params_wrong_type(self):
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
        }
        validator = ResourceValidator(schema, "Widget")
        is_valid, error, params = validator.validate({"count": "not_a_number"})
        assert is_valid is False
        assert "Widget validation error" in error

    def test_extra_properties_allowed_by_default(self):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        validator = ResourceValidator(schema, "Loose")
        is_valid, _, params = validator.validate({"name": "test", "extra": "ok"})
        assert is_valid is True


class TestCreateResponse:
    """Tests for the create_response helper."""

    def test_success_with_data_dict(self):
        result = create_response(True, data={"key": "value"})
        assert result == {"success": True, "data": {"key": "value"}}

    def test_success_with_string_data(self):
        result = create_response(True, data="abc123")
        assert result == {"success": True, "id": "abc123"}

    def test_success_no_data(self):
        result = create_response(True)
        assert result == {"success": True}

    def test_failure_with_error(self):
        result = create_response(False, error="Something went wrong")
        assert result == {"success": False, "error": "Something went wrong"}

    def test_failure_no_error(self):
        result = create_response(False)
        assert result == {"success": False}
