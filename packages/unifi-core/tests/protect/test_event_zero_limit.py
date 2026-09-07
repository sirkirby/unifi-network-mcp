"""Zero event limits are local empty results across Protect query paths."""

import pytest
from unifi_core.protect.managers.event_manager import EventManager


@pytest.mark.asyncio
@pytest.mark.parametrize("filters", [{}, {"camera_id": "camera"}, {"metadata_fields": ["score"]}])
async def test_zero_limit_never_accesses_controller(filters):
    class NoControllerAccess:
        @property
        def client(self):
            raise AssertionError("zero results must not access the controller")

    manager = EventManager(NoControllerAccess())
    assert await manager.list_events(limit=0, **filters) == []
