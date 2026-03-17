"""Smoke tests for the UniFi Protect MCP server scaffold."""


def test_package_importable():
    """Verify the unifi_protect_mcp package can be imported."""
    import unifi_protect_mcp

    assert unifi_protect_mcp.__doc__ is not None


def test_managers_importable():
    """Verify all manager stubs can be imported."""
    from unifi_protect_mcp.managers.camera_manager import CameraManager
    from unifi_protect_mcp.managers.chime_manager import ChimeManager
    from unifi_protect_mcp.managers.connection_manager import ProtectConnectionManager
    from unifi_protect_mcp.managers.event_manager import EventManager
    from unifi_protect_mcp.managers.light_manager import LightManager
    from unifi_protect_mcp.managers.liveview_manager import LiveviewManager
    from unifi_protect_mcp.managers.recording_manager import RecordingManager
    from unifi_protect_mcp.managers.sensor_manager import SensorManager
    from unifi_protect_mcp.managers.system_manager import SystemManager

    # Verify all classes can be instantiated with a mock connection manager
    cm = ProtectConnectionManager(host="test", username="test", password="test")
    assert CameraManager(cm) is not None
    assert ChimeManager(cm) is not None
    assert EventManager(cm) is not None
    assert LightManager(cm) is not None
    assert LiveviewManager(cm) is not None
    assert RecordingManager(cm) is not None
    assert SensorManager(cm) is not None
    assert SystemManager(cm) is not None


def test_categories_importable():
    """Verify categories module loads correctly."""
    from unifi_protect_mcp.categories import PROTECT_CATEGORY_MAP, TOOL_MODULE_MAP

    assert isinstance(PROTECT_CATEGORY_MAP, dict)
    assert "camera" in PROTECT_CATEGORY_MAP
    assert "event" in PROTECT_CATEGORY_MAP
    assert "recording" in PROTECT_CATEGORY_MAP
    assert "light" in PROTECT_CATEGORY_MAP
    assert "sensor" in PROTECT_CATEGORY_MAP
    assert "chime" in PROTECT_CATEGORY_MAP
    assert "liveview" in PROTECT_CATEGORY_MAP
    assert "system" in PROTECT_CATEGORY_MAP
    assert isinstance(TOOL_MODULE_MAP, dict)


def test_tool_index_importable():
    """Verify tool_index module loads correctly."""
    from unifi_protect_mcp.tool_index import TOOL_REGISTRY, ToolMetadata, register_tool

    assert isinstance(TOOL_REGISTRY, dict)
    assert ToolMetadata is not None
    assert register_tool is not None


def test_schemas_importable():
    """Verify schemas module loads correctly."""
    from unifi_protect_mcp.schemas import ProtectResourceRegistry

    assert ProtectResourceRegistry.get_schema("nonexistent") == {}


def test_validators_importable():
    """Verify validators module loads correctly."""
    from unifi_protect_mcp.validators import ResourceValidator, create_response

    assert ResourceValidator is not None
    resp = create_response(success=True, data={"test": 1})
    assert resp["success"] is True
    assert resp["data"] == {"test": 1}

    err = create_response(success=False, error="test error")
    assert err["success"] is False
    assert err["error"] == "test error"


def test_validator_registry_importable():
    """Verify validator_registry module loads correctly."""
    from unifi_protect_mcp.validator_registry import ProtectValidatorRegistry

    is_valid, err, params = ProtectValidatorRegistry.validate("nonexistent", {})
    assert is_valid is False
    assert "No validator found" in err


def test_config_helpers_importable():
    """Verify config helpers module loads correctly."""
    from unifi_protect_mcp.utils.config_helpers import parse_config_bool

    assert parse_config_bool("true") is True
    assert parse_config_bool("false") is False
    assert parse_config_bool(None, default=True) is True


def test_connection_manager_properties():
    """Verify ProtectConnectionManager stores connection params."""
    from unifi_protect_mcp.managers.connection_manager import ProtectConnectionManager

    cm = ProtectConnectionManager(
        host="192.168.1.1",
        username="admin",
        password="secret",
        port=7443,
        site="default",
        verify_ssl=True,
    )
    assert cm.host == "192.168.1.1"
    assert cm.username == "admin"
    assert cm.port == 7443
    assert cm.verify_ssl is True
    assert cm.is_connected is False


def test_protect_category_map_values():
    """Verify category map values match config.yaml permissions keys."""
    from unifi_protect_mcp.categories import PROTECT_CATEGORY_MAP

    expected_values = {"cameras", "events", "recordings", "lights", "sensors", "chimes", "liveviews", "system"}
    assert set(PROTECT_CATEGORY_MAP.values()) == expected_values
