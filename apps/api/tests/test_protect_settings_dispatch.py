"""Protect settings must execute on confirmation and report partial failures."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from unifi_api.services.actions import MutationPreview, dispatch_action
from unifi_api.services.manifest import ManifestRegistry


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "domain,settings,method",
    [
        ("camera", {"hdr_mode": "superHdr"}, "apply_camera_settings"),
        ("light", {"is_light_on": True}, "apply_light_settings"),
    ],
)
@pytest.mark.parametrize("confirm", [False, True])
@pytest.mark.parametrize("applied", [[], ["name=new"]])
@pytest.mark.parametrize("failed", [False, True])
async def test_protect_settings_dispatch(domain, settings, method, confirm, applied, failed):
    manager = MagicMock()
    result = {"applied": applied}
    if failed:
        result["errors"] = ["controller refused setting"]
    write = AsyncMock(return_value=result)
    setattr(manager, method, write)
    factory = MagicMock()
    factory.get_domain_manager = AsyncMock(return_value=manager)
    kwargs = dict(
        registry=ManifestRegistry.load(),
        factory=factory,
        session=MagicMock(),
        tool_name="protect_update_camera_settings" if domain == "camera" else "protect_update_light",
        controller_id="controller",
        controller_products=["protect"],
        site="default",
        args={f"{domain}_id": "device", "settings": settings},
        confirm=confirm,
    )
    response = await dispatch_action(**kwargs)
    if confirm:
        assert response == result
        from unifi_api.serializers.protect.cameras import CameraMutationAckSerializer
        from unifi_api.serializers.protect.lights import LightMutationAckSerializer

        serializer = CameraMutationAckSerializer() if domain == "camera" else LightMutationAckSerializer()
        envelope = serializer.serialize_action(response, tool_name=kwargs["tool_name"])
        assert envelope["success"] is not failed
        assert envelope["data"]["applied"] == applied
        if failed:
            assert "controller refused setting" in envelope["error"]
    else:
        assert isinstance(response, MutationPreview)
    if confirm:
        write.assert_awaited_once_with(
            **{
                f"{domain}_id": "device",
                "settings": {"hdr_mode": "always"} if domain == "camera" else {"light_on": True},
            }
        )
    else:
        factory.get_domain_manager.assert_not_awaited()
        write.assert_not_awaited()
