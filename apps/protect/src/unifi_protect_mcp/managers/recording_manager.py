"""Recording management for UniFi Protect.

Provides methods to query recording status, export video clips, and manage
recordings via the uiprotect API.  Recordings are accessed through cameras
using time-range-based queries rather than discrete recording objects.

Key API surface:
- ``Camera.get_video(start, end, ...)`` -- export MP4 clip (bytes)
- ``Camera.recording_settings`` -- current recording configuration
- ``Camera.is_recording`` / ``Camera.has_recordings`` -- state flags
- ``Camera.stats.video`` -- recording time range metadata
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from unifi_protect_mcp.managers.connection_manager import ProtectConnectionManager

logger = logging.getLogger(__name__)


class RecordingManager:
    """Domain logic for UniFi Protect recordings."""

    def __init__(self, connection_manager: ProtectConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_camera(self, camera_id: str):
        """Retrieve a Camera object by ID, raising ValueError if not found."""
        cameras = self._cm.client.bootstrap.cameras
        camera = cameras.get(camera_id)
        if camera is None:
            raise ValueError(f"Camera not found: {camera_id}")
        return camera

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    async def get_recording_status(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        """Return current recording state for one or all cameras.

        For each camera, reports recording mode, whether it is actively
        recording, and available recording time range from stats.
        """
        cameras = self._cm.client.bootstrap.cameras

        if camera_id:
            camera = self._get_camera(camera_id)
            return {
                "cameras": [self._format_recording_status(camera)],
                "count": 1,
            }

        results: List[Dict[str, Any]] = []
        for cam in cameras.values():
            results.append(self._format_recording_status(cam))

        return {
            "cameras": results,
            "count": len(results),
        }

    @staticmethod
    def _format_recording_status(camera) -> Dict[str, Any]:
        """Format recording status for a single camera."""
        recording_mode = None
        if camera.recording_settings:
            recording_mode = str(camera.recording_settings.mode.value)

        # Extract recording time range from stats if available
        video_stats: Dict[str, Any] = {}
        if camera.stats and hasattr(camera.stats, "video") and camera.stats.video:
            video = camera.stats.video
            video_stats = {
                "recording_start": video.recording_start.isoformat()
                if hasattr(video, "recording_start") and video.recording_start
                else None,
                "recording_end": video.recording_end.isoformat()
                if hasattr(video, "recording_end") and video.recording_end
                else None,
                "timelapse_start": video.timelapse_start.isoformat()
                if hasattr(video, "timelapse_start") and video.timelapse_start
                else None,
                "timelapse_end": video.timelapse_end.isoformat()
                if hasattr(video, "timelapse_end") and video.timelapse_end
                else None,
            }

        return {
            "camera_id": camera.id,
            "camera_name": camera.name,
            "recording_mode": recording_mode,
            "is_recording": camera.is_recording,
            "has_recordings": getattr(camera, "has_recordings", None),
            "video_stats": video_stats,
        }

    async def list_recordings(
        self,
        camera_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Return recording availability info for a camera in a time range.

        Note: uiprotect does not provide a discrete list of recording segments.
        Instead, recordings are accessible as continuous time ranges.  This
        method reports the available recording time window and whether footage
        exists for the requested period based on camera stats.
        """
        camera = self._get_camera(camera_id)

        # Default time range: last 24 hours
        if end is None:
            end = datetime.now(tz=start.tzinfo if start and start.tzinfo else None)
        if start is None:
            start = end - timedelta(hours=24)

        # Gather available recording window from stats
        recording_info: Dict[str, Any] = {
            "camera_id": camera_id,
            "camera_name": camera.name,
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "is_recording": camera.is_recording,
            "has_recordings": getattr(camera, "has_recordings", None),
        }

        recording_mode = None
        if camera.recording_settings:
            recording_mode = str(camera.recording_settings.mode.value)
        recording_info["recording_mode"] = recording_mode

        # Video stats for overall recording window
        if camera.stats and hasattr(camera.stats, "video") and camera.stats.video:
            video = camera.stats.video
            rec_start = getattr(video, "recording_start", None)
            rec_end = getattr(video, "recording_end", None)
            recording_info["available_start"] = rec_start.isoformat() if rec_start else None
            recording_info["available_end"] = rec_end.isoformat() if rec_end else None
        else:
            recording_info["available_start"] = None
            recording_info["available_end"] = None

        recording_info["note"] = (
            "UniFi Protect stores recordings as continuous streams, not discrete segments. "
            "Use protect_export_clip to download a specific time range as MP4."
        )

        return recording_info

    async def export_clip(
        self,
        camera_id: str,
        start: datetime,
        end: datetime,
        channel_index: int = 0,
        fps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Export a video clip from a camera for a given time range.

        Returns metadata about the export.  The actual video bytes are large
        and not suitable for MCP tool responses; this method returns size and
        availability information.

        For timelapse exports, pass ``fps`` (e.g., 4 for 60x, 8 for 120x,
        20 for 300x, 40 for 600x).
        """
        camera = self._get_camera(camera_id)

        duration = end - start
        if duration.total_seconds() <= 0:
            raise ValueError("End time must be after start time.")
        if duration.total_seconds() > 7200:  # 2 hours max
            raise ValueError("Maximum export duration is 2 hours. Please specify a shorter range.")

        # Build kwargs for the API call
        kwargs: Dict[str, Any] = {
            "start": start,
            "end": end,
            "channel_index": channel_index,
        }
        if fps is not None:
            kwargs["fps"] = fps

        # Attempt the export
        video_bytes = await camera.get_video(**kwargs)

        if video_bytes is None:
            return {
                "camera_id": camera_id,
                "camera_name": camera.name,
                "exported": False,
                "message": "No recording available for the requested time range.",
                "start": start.isoformat(),
                "end": end.isoformat(),
            }

        return {
            "camera_id": camera_id,
            "camera_name": camera.name,
            "exported": True,
            "size_bytes": len(video_bytes),
            "duration_seconds": int(duration.total_seconds()),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "channel_index": channel_index,
            "is_timelapse": fps is not None,
            "fps": fps,
            "content_type": "video/mp4",
            "note": (
                "Video clip exported successfully. The clip data is available "
                "but too large to include inline. Use the Protect web UI or "
                "a direct API call to download the file."
            ),
        }

    # ------------------------------------------------------------------
    # Mutation methods (preview/confirm pattern)
    # ------------------------------------------------------------------

    async def delete_recording(
        self,
        camera_id: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """Return preview data for deleting recordings in a time range.

        Note: uiprotect does not expose a public API for deleting individual
        recording segments.  Recording retention is managed at the NVR level
        via storage settings.  This method returns a preview explaining the
        limitation.
        """
        camera = self._get_camera(camera_id)

        return {
            "camera_id": camera_id,
            "camera_name": camera.name,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "supported": False,
            "message": (
                "Individual recording deletion is not supported by the uiprotect API. "
                "Recording retention is managed automatically by the NVR based on "
                "storage capacity and retention settings. Use the Protect web UI "
                "to manage storage settings."
            ),
        }

    # TODO: generate_timelapse is not a separate API in uiprotect.
    # Timelapse exports are supported via Camera.get_video(fps=N).
    # This is exposed through the export_clip method with the fps parameter.
