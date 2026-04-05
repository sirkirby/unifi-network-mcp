"""Alarm Manager control for UniFi Protect.

Wraps the private ``/proxy/protect/api/arm/*`` endpoints used by the
UniFi Protect Alarm Manager (Protect 6.1+) to arm/disarm the system.
The ``uiprotect`` library does not expose these endpoints natively, so
this manager calls them directly via ``ProtectApiClient.api_request``.

Endpoints (verified against Protect 7.0)
-----------------------------------------
- ``GET  arm/profiles``    -- list all arm profile definitions
- ``PATCH arm``            -- select active profile, body ``{"armProfileId": "..."}``
- ``POST arm/enable``      -- arm the system (empty body)
- ``POST arm/disable``     -- disarm the system (empty body)

Current armed state lives in ``nvr.armMode`` (single state per system,
not per-profile):

.. code-block:: json

    {
      "status": "disabled",           // or "active"/"armed" when on
      "armProfileId": "<id>",         // currently selected profile
      "armedAt": 1775400000000,
      "willBeArmedAt": null,
      "breachDetectedAt": 1775310901100,
      "breachEventCount": 0,
      "breachTriggerEventId": null,
      "breachEventId": "..."
    }
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from unifi_protect_mcp.managers.connection_manager import ProtectConnectionManager

logger = logging.getLogger(__name__)

# Values of ``nvr.armMode.status`` that mean "not armed".
_DISARMED_STATUSES = {"disabled", "disarmed", "off", "inactive"}


class AlarmManager:
    """Domain logic for the UniFi Protect Alarm Manager."""

    def __init__(self, connection_manager: ProtectConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_arm_profiles(self) -> List[Dict[str, Any]]:
        """Return all configured arm profile definitions.

        ``GET arm/profiles`` returns a flat array of profile objects.
        """
        data = await self._cm.client.api_request("arm/profiles", method="get")
        if not isinstance(data, list):
            logger.warning("Unexpected arm/profiles shape: %r", type(data))
            return []

        return [self._format_profile(p) for p in data if isinstance(p, dict)]

    async def get_arm_state(self) -> Dict[str, Any]:
        """Return the current Alarm Manager state.

        Merges ``nvr.armMode`` (status + active profile id) with
        ``arm/profiles`` (profile names/metadata) into a single dict.
        """
        nvr_data, profiles = await self._fetch_state()

        arm_mode = (nvr_data or {}).get("armMode") or {}
        status = arm_mode.get("status")
        active_profile_id = arm_mode.get("armProfileId")

        # Look up the active profile's name if we have it
        active_profile = next(
            (p for p in profiles if p["id"] == active_profile_id),
            None,
        )

        return {
            "armed": self._is_armed_status(status),
            "status": status,
            "active_profile_id": active_profile_id,
            "active_profile_name": active_profile["name"] if active_profile else None,
            "armed_at": _ms_to_iso(arm_mode.get("armedAt")),
            "will_be_armed_at": _ms_to_iso(arm_mode.get("willBeArmedAt")),
            "breach_detected_at": _ms_to_iso(arm_mode.get("breachDetectedAt")),
            "breach_event_count": arm_mode.get("breachEventCount", 0),
            "profiles": profiles,
        }

    async def _fetch_state(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Fetch nvr + arm/profiles in one pair of calls."""
        nvr_data = await self._cm.client.api_request("nvr", method="get")
        profiles_raw = await self._cm.client.api_request("arm/profiles", method="get")

        profiles: List[Dict[str, Any]] = []
        if isinstance(profiles_raw, list):
            profiles = [self._format_profile(p) for p in profiles_raw if isinstance(p, dict)]

        if not isinstance(nvr_data, dict):
            nvr_data = {}

        return nvr_data, profiles

    @staticmethod
    def _format_profile(p: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": p.get("id"),
            "name": p.get("name"),
            "record_everything": p.get("recordEverything", False),
            "activation_delay_ms": p.get("activationDelay"),
            "schedule_count": len(p.get("schedules") or []),
            "automation_count": len(p.get("automations") or []),
        }

    @staticmethod
    def _is_armed_status(status: Optional[str]) -> bool:
        if not status:
            return False
        return str(status).lower() not in _DISARMED_STATUSES

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _resolve_profile_id(self, profile_id: Optional[str]) -> str:
        """Return ``profile_id`` or fall back to the currently selected one.

        Fall-back order when ``profile_id`` is ``None``:
          1. ``nvr.armMode.armProfileId`` (the currently selected profile)
          2. The first profile returned by ``arm/profiles``
        """
        if profile_id:
            return profile_id

        nvr_data, profiles = await self._fetch_state()
        current = (nvr_data.get("armMode") or {}).get("armProfileId")
        if current:
            return str(current)

        if profiles:
            first_id = profiles[0].get("id")
            if first_id:
                return str(first_id)

        raise ValueError(
            "No arm profiles found. Configure Alarm Manager in the Protect UI first, or pass profile_id explicitly."
        )

    async def _profile_name(self, profile_id: str) -> Optional[str]:
        try:
            profiles = await self.list_arm_profiles()
        except Exception:
            return None
        for p in profiles:
            if p.get("id") == profile_id:
                return p.get("name")
        return None

    async def _select_profile(self, profile_id: str) -> None:
        """PATCH ``arm`` to set which profile is active."""
        await self._cm.client.api_request(
            "arm",
            method="patch",
            json={"armProfileId": profile_id},
        )

    # ------------------------------------------------------------------
    # Preview (for confirm=false tool responses)
    # ------------------------------------------------------------------

    async def preview_arm(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Return current + proposed state for the arm action preview."""
        nvr_data, profiles = await self._fetch_state()
        arm_mode = nvr_data.get("armMode") or {}
        current_profile_id = arm_mode.get("armProfileId")
        currently_armed = self._is_armed_status(arm_mode.get("status"))

        target_id = profile_id or current_profile_id
        if not target_id and profiles:
            target_id = profiles[0].get("id")
        if not target_id:
            raise ValueError(
                "No arm profiles found. Configure Alarm Manager in the Protect UI first, or pass profile_id explicitly."
            )
        target_id = str(target_id)
        target_name = next((p["name"] for p in profiles if p["id"] == target_id), None)

        return {
            "target_profile_id": target_id,
            "target_profile_name": target_name,
            "current_state": {
                "armed": currently_armed,
                "active_profile_id": current_profile_id,
                "status": arm_mode.get("status"),
            },
            "proposed_changes": {
                "armed": True,
                "active_profile_id": target_id,
            },
        }

    async def preview_disarm(self) -> Dict[str, Any]:
        """Return current state for the disarm action preview."""
        state = await self.get_arm_state()
        return {
            "active_profile_id": state["active_profile_id"],
            "active_profile_name": state["active_profile_name"],
            "current_state": {
                "armed": state["armed"],
                "status": state["status"],
            },
            "proposed_changes": {"armed": False},
        }

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def arm(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Arm the Alarm Manager.

        1. Selects ``profile_id`` via ``PATCH arm`` (or uses current selection).
        2. Activates via ``POST arm/enable``.

        If ``profile_id`` is ``None``, the currently selected profile (from
        ``nvr.armMode.armProfileId``) is used and no PATCH is issued.

        Idempotent: if already armed with the same profile, returns without
        making the POST call (the API returns 400 on duplicate arm).
        """
        nvr_data, profiles = await self._fetch_state()
        arm_mode = nvr_data.get("armMode") or {}
        current_status = arm_mode.get("status")
        current_profile_id = arm_mode.get("armProfileId")
        currently_armed = self._is_armed_status(current_status)

        pid = profile_id or current_profile_id
        if not pid:
            # No currently-selected profile and none passed; pick first available.
            if profiles:
                pid = profiles[0].get("id")
            if not pid:
                raise ValueError(
                    "No arm profiles found. Configure Alarm Manager in the "
                    "Protect UI first, or pass profile_id explicitly."
                )
        pid = str(pid)

        name = next((p["name"] for p in profiles if p["id"] == pid), None)

        # Short-circuit if already armed with the same profile.
        if currently_armed and pid == current_profile_id:
            logger.info("Already armed with profile %s (%s) — no-op", pid, name)
            return {
                "armed": True,
                "profile_id": pid,
                "profile_name": name,
                "already_armed": True,
            }

        # Switching profiles while armed is not supported: the POST arm/enable
        # endpoint returns 400 when the system is already armed. Require the
        # caller to disarm first so the flow is always disabled -> patch -> enable.
        if currently_armed and profile_id and profile_id != current_profile_id:
            raise ValueError(
                f"Cannot switch arm profile while system is armed "
                f"(currently armed with profile {current_profile_id!r}). "
                f"Disarm first, then arm with the new profile."
            )

        # Select the profile (PATCH) when the caller explicitly passed one that
        # differs from the current selection.
        if profile_id and profile_id != current_profile_id:
            await self._select_profile(pid)

        logger.info("Arming Protect Alarm Manager profile %s (%s)", pid, name)
        await self._cm.client.api_request("arm/enable", method="post")

        return {
            "armed": True,
            "profile_id": pid,
            "profile_name": name,
        }

    async def disarm(self) -> Dict[str, Any]:
        """Disarm the Alarm Manager.

        ``POST arm/disable`` is a single system-wide disarm — no profile id
        is required (and none is accepted by the endpoint).

        Idempotent: if already disarmed, returns without making the POST call
        (the API returns 400 "Attempted to disarm the alarm when it is not
        armed" otherwise).
        """
        state = await self.get_arm_state()
        if not state["armed"]:
            logger.info("Already disarmed — no-op")
            return {"armed": False, "already_disarmed": True}

        logger.info("Disarming Protect Alarm Manager")
        await self._cm.client.api_request("arm/disable", method="post")

        return {"armed": False}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ms_to_iso(value: Any) -> Optional[str]:
    """Convert a millisecond unix timestamp to an ISO-8601 UTC string."""
    if value is None:
        return None
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
