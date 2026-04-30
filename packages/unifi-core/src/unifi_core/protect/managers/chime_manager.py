"""Chime management for UniFi Protect.

Provides methods to list, update, and trigger UniFi Protect chime devices
via the uiprotect bootstrap data.

Key API surface on ``Chime``:
- ``play(volume=None, repeat_times=None, ringtone_id=None, track_no=None)`` -- play chime tone
- ``play_buzzer()`` -- play buzzer sound
- ``set_volume(level)`` -- set speaker volume (deprecated, use set_volume_for_camera_public)
- ``set_repeat_times(value)`` -- set repeat count (deprecated, use set_ring_settings_public)
- ``ring_settings`` -- per-camera ring configuration
- ``speaker_track_list`` -- available ringtones/tracks
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from unifi_core.exceptions import UniFiNotFoundError
from unifi_core.protect.managers.connection_manager import ProtectConnectionManager

logger = logging.getLogger(__name__)


class ChimeManager:
    """Domain logic for UniFi Protect chimes."""

    def __init__(self, connection_manager: ProtectConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_chime(self, chime_id: str):
        """Retrieve a Chime object by ID, raising UniFiNotFoundError if not found."""
        chimes = self._cm.client.bootstrap.chimes
        chime = chimes.get(chime_id)
        if chime is None:
            raise UniFiNotFoundError("chime", chime_id)
        return chime

    @staticmethod
    def _format_chime_summary(chime) -> Dict[str, Any]:
        """Format a chime into a summary dict with essential fields."""
        # Ring settings per camera
        ring_settings: List[Dict[str, Any]] = []
        for rs in chime.ring_settings or []:
            ring_settings.append(
                {
                    "camera_id": rs.camera_id,
                    "volume": rs.volume,
                    "repeat_times": rs.repeat_times,
                    "ringtone_id": rs.ringtone_id,
                    "track_no": rs.track_no,
                }
            )

        # Available tracks
        tracks: List[Dict[str, Any]] = []
        for track in chime.speaker_track_list or []:
            tracks.append(
                {
                    "track_no": track.track_no,
                    "name": track.name,
                    "state": track.state,
                }
            )

        return {
            "id": chime.id,
            "name": chime.name,
            "type": str(chime.type),
            "model": chime.market_name or str(chime.type),
            "state": str(chime.state.value) if chime.state else None,
            "is_connected": chime.is_connected,
            "firmware_version": chime.firmware_version,
            "last_seen": chime.last_seen.isoformat() if chime.last_seen else None,
            "volume": chime.volume,
            "last_ring": chime.last_ring.isoformat() if chime.last_ring else None,
            "camera_ids": list(chime.camera_ids) if chime.camera_ids else [],
            "repeat_times": chime.repeat_times,
            "ring_settings": ring_settings,
            "available_tracks": tracks,
        }

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    async def list_chimes(self) -> List[Dict[str, Any]]:
        """Return all chimes as summary dicts."""
        chimes = self._cm.client.bootstrap.chimes
        return [self._format_chime_summary(chime) for chime in chimes.values()]

    # ------------------------------------------------------------------
    # Mutation methods (preview / apply)
    # ------------------------------------------------------------------

    async def update_chime(self, chime_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Return current and proposed chime state for preview.

        Supported settings keys:
        - volume: int (0-100) -- speaker volume
        - repeat_times: int (1-6) -- how many times to repeat ring
        - name: str -- device name
        """
        chime = self._get_chime(chime_id)

        current_state: Dict[str, Any] = {}
        proposed_changes: Dict[str, Any] = {}

        for key, value in settings.items():
            if key == "volume":
                current_state["volume"] = chime.volume
                proposed_changes["volume"] = value
            elif key == "repeat_times":
                current_state["repeat_times"] = chime.repeat_times
                proposed_changes["repeat_times"] = value
            elif key == "name":
                current_state["name"] = chime.name
                proposed_changes["name"] = value
            else:
                logger.warning("Unknown chime setting key: %s", key)

        return {
            "chime_id": chime_id,
            "chime_name": chime.name,
            "current_state": current_state,
            "proposed_changes": proposed_changes,
        }

    async def apply_chime_settings(self, chime_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Apply chime settings after confirmation."""
        chime = self._get_chime(chime_id)
        applied: List[str] = []
        errors: List[str] = []

        for key, value in settings.items():
            try:
                if key == "volume":
                    await chime.set_volume(int(value))
                    applied.append(f"volume={value}")
                elif key == "repeat_times":
                    await chime.set_repeat_times(int(value))
                    applied.append(f"repeat_times={value}")
                elif key == "name":
                    await chime.set_name(str(value))
                    applied.append(f"name={value}")
                else:
                    errors.append(f"Unknown setting: {key}")
            except Exception as exc:
                logger.error("Error applying chime setting %s=%s: %s", key, value, exc, exc_info=True)
                errors.append(f"{key}: {exc}")

        result: Dict[str, Any] = {
            "chime_id": chime_id,
            "chime_name": chime.name,
            "applied": applied,
        }
        if errors:
            result["errors"] = errors

        return result

    async def trigger_chime(
        self,
        chime_id: str,
        volume: Optional[int] = None,
        repeat_times: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Play the chime tone.

        Uses the Chime.play() API to trigger the sound.
        """
        chime = self._get_chime(chime_id)

        kwargs: Dict[str, Any] = {}
        if volume is not None:
            kwargs["volume"] = volume
        if repeat_times is not None:
            kwargs["repeat_times"] = repeat_times

        await chime.play(**kwargs)

        return {
            "chime_id": chime_id,
            "chime_name": chime.name,
            "triggered": True,
            "volume": volume if volume is not None else chime.volume,
            "repeat_times": repeat_times if repeat_times is not None else chime.repeat_times,
        }
