"""A MAC address must not survive into a log line or a re-raised controller error.

Credential scrubbing does not cover a MAC: it is not a secret-keyed value, so
``collect_secret_values`` never sees it and the API audit sink stores whatever the
controller quoted back. Client targeting on firewall policies, ACL rules, blocks
and renames all put MACs in the record a rejection echoes.
"""

import json
import logging

import pytest
from aiounifi.errors import ResponseError
from aiounifi.models.api import ApiRequestV2
from unifi_core.mac import mask_exception_macs
from unifi_core.network.managers.connection_manager import ConnectionManager

MAC = "aa:bb:cc:dd:ee:ff"
DASHED = "AA-BB-CC-DD-EE-FF"


class _Session:
    closed = False

    async def close(self):
        return None


class _Config:
    def __init__(self):
        self.session = _Session()


class _Connectivity:
    def __init__(self):
        self.can_retry_login = True
        self.config = _Config()
        self.is_unifi_os = True


class _Controller:
    def __init__(self, raiser):
        self.connectivity = _Connectivity()
        self._raiser = raiser

    async def login(self):
        self.connectivity.can_retry_login = False

    async def request(self, api_request):
        raise self._raiser()


def _manager(controller):
    manager = ConnectionManager("192.168.1.1", "admin", "pw")
    manager.controller = controller
    manager._aiohttp_session = controller.connectivity.config.session
    manager._initialized = True
    manager._auth_generation = 1
    return manager


def _rejected_policy_write():
    body = {
        "meta": {"rc": "error", "msg": "api.err.InvalidPayload"},
        "data": [{"name": "Admin only", "source": {"matching_target": "CLIENT", "client_macs": [MAC]}}],
    }
    return ResponseError(json.dumps(body))


@pytest.mark.asyncio
async def test_a_rejected_client_targeted_write_keeps_the_mac_out_of_the_log_and_the_error(caplog):
    manager = _manager(_Controller(_rejected_policy_write))
    request = ApiRequestV2(
        method="post",
        path="/firewall-policies",
        data={"name": "Admin only", "source": {"matching_target": "CLIENT", "client_macs": [MAC]}},
    )

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(Exception) as excinfo:
            await manager.request(request)

    assert MAC not in caplog.text
    assert MAC not in str(excinfo.value)
    assert "[redacted]" in str(excinfo.value)


class TestMaskExceptionMacs:
    def test_masks_a_mac_inside_a_decoded_response_dict(self):
        error = ValueError({"data": [{"client_macs": [MAC, DASHED]}]})

        mask_exception_macs(error)

        assert MAC not in str(error)
        assert DASHED.lower() not in str(error).lower()

    def test_follows_the_cause_chain(self):
        inner = ValueError(f"rejected {MAC}")
        outer = RuntimeError("wrapped")
        outer.__cause__ = inner

        mask_exception_macs(outer)

        assert MAC not in str(inner)

    def test_a_cycle_in_the_chain_terminates(self):
        a = ValueError(f"a {MAC}")
        b = ValueError("b")
        a.__cause__ = b
        b.__cause__ = a

        mask_exception_macs(a)

        assert MAC not in str(a)

    def test_leaves_an_identifier_that_is_not_a_mac_alone(self):
        error = ValueError("policy 68a1f0c2d4e5b6a7c8d9e0f1 rejected")

        mask_exception_macs(error)

        assert "68a1f0c2d4e5b6a7c8d9e0f1" in str(error)

    def test_returns_the_same_exception_object(self):
        error = ValueError(MAC)
        assert mask_exception_macs(error) is error
