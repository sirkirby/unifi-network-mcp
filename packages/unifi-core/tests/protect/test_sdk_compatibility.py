"""Check the installed SDK, rather than mocks that can invent removed methods."""

import inspect

import pytest
from uiprotect.data import Camera, Light


@pytest.mark.parametrize(
    ("model", "method"),
    [
        (Camera, "set_hdr_mode"),
        (Camera, "set_mic_volume"),
        (Light, "set_light"),
        (Light, "set_led_level"),
        (Light, "set_sensitivity"),
        (Light, "set_duration"),
    ],
)
def test_manager_write_methods_exist_in_installed_sdk(model: type, method: str) -> None:
    """Confirmed camera/light updates require these session-auth async methods."""
    assert inspect.iscoroutinefunction(getattr(model, method, None)), (
        f"{model.__name__}.{method} is unavailable; migrate the manager before upgrading uiprotect"
    )
