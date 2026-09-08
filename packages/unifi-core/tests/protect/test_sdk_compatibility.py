"""Check the installed SDK, rather than mocks that can invent removed methods."""

import inspect

import pytest
from uiprotect.data import Camera, Chime, Light


@pytest.mark.parametrize(
    ("model", "method"),
    [
        (Camera, "set_hdr_mode_public"),
        (Camera, "set_mic_volume_public"),
        (Light, "set_light_public"),
        (Light, "set_led_level_public"),
        (Light, "set_sensitivity_public"),
        (Light, "set_duration_public"),
        (Camera, "set_ir_led_model"),
        (Camera, "set_status_light"),
        (Camera, "set_speaker_volume"),
        (Camera, "set_name"),
        (Camera, "set_motion_detection"),
        (Camera, "set_recording_mode"),
        (Camera, "save_device"),
        (Camera, "ptz_goto_preset_public"),
        (Camera, "reboot"),
        (Light, "set_status_light"),
        (Light, "set_name"),
        (Chime, "set_volume"),
        (Chime, "set_repeat_times"),
        (Chime, "set_name"),
        (Chime, "play"),
    ],
)
def test_manager_write_methods_exist_in_installed_sdk(model: type, method: str) -> None:
    """Confirmed camera/light updates require these public API async methods."""
    assert inspect.iscoroutinefunction(getattr(model, method, None)), (
        f"{model.__name__}.{method} is unavailable; migrate the manager before upgrading uiprotect"
    )
