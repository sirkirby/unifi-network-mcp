"""Protect Alarm Manager serializers (Phase 4A PR2 Cluster 3).

Covers:
  * ``protect_alarm_get_status`` — DETAIL detail of current arm state.
    Manager method: ``AlarmManager.get_arm_state``.
  * ``protect_alarm_list_profiles`` — DETAIL pass-through of the
    ``{profiles: [...], count: N}`` wrapper the tool layer constructs.
    (Plan asked for LIST kind, but the tool layer wraps the bare list
    in a count-bearing dict — so DETAIL pass-through is the contract-correct
    choice. Same pattern Cluster 2 used for ``protect_recent_events``.)
  * ``protect_alarm_arm`` / ``protect_alarm_disarm`` — DETAIL pass-through
    for the post-confirm ack dict (``{armed, profile_id, profile_name}`` /
    ``{armed, already_disarmed?}``). Preview dicts also flow through cleanly.

Profile field shape is the manager's flattened form:
``id, name, record_everything, activation_delay_ms, schedule_count,
automation_count``. The plan's ``schedule, trigger_camera_ids`` shape does
not match what the manager actually returns — recorded in the test docstring.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "protect_alarm_get_status": {"kind": RenderKind.DETAIL},
    },
)
class AlarmStatusSerializer(Serializer):
    """Pass-through for the alarm status dict produced by the tool layer."""

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj: Any) -> dict:
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}


@register_serializer(
    tools={
        "protect_alarm_list_profiles": {"kind": RenderKind.DETAIL},
    },
)
class AlarmProfileSerializer(Serializer):
    """Pass-through for the ``{profiles, count}`` wrapper the tool returns.

    Per-profile fields (forwarded as-is): ``id``, ``name``,
    ``record_everything``, ``activation_delay_ms``, ``schedule_count``,
    ``automation_count``.
    """

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj: Any) -> dict:
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list):
            # Defensive: if a caller hands us the bare list, wrap it.
            return {"profiles": list(obj), "count": len(obj)}
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}


@register_serializer(
    tools={
        "protect_alarm_arm": {"kind": RenderKind.DETAIL},
        "protect_alarm_disarm": {"kind": RenderKind.DETAIL},
    },
)
class AlarmMutationAckSerializer(Serializer):
    """Pass-through for arm/disarm acks. Coerces a bare bool into a dict."""

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj: Any) -> dict:
        if isinstance(obj, bool):
            return {"armed": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
