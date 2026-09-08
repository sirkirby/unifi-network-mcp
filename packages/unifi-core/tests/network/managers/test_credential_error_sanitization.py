"""Credential values must not survive into logs or re-raised errors.

A controller exception that quotes the submitted
request reached ``ConnectionManager``'s raw exception log, ``SystemManager``'s
raw response/exception log and (via the unchanged exception) the API audit
sink. These tests drive the real managers with a fake transport that raises
an error carrying a sentinel, and assert the sentinel is gone from every
log line and from the exception the caller receives.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import quote

import pytest
from aiohttp import ClientError, ClientResponseError, RequestInfo
from aiounifi.errors import LoginRequired, RequestError, ResponseError
from aiounifi.models.api import ApiRequest
from unifi_core.network.managers.connection_manager import ConnectionManager
from unifi_core.network.managers.system_manager import SystemManager

from tests.secret_assertions import ESCAPED_SECRET, assert_unrecoverable

SENTINEL = "SENTINEL-submitted-secret-7f3a"
LOGIN_SENTINEL = "SENTINEL-login-secret-91c2"
UNKNOWN_SECRET = "SENTINEL-controller-only-token-49ac"


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
    """Fake aiounifi controller whose request always fails with the given error."""

    def __init__(self, raiser):
        self.connectivity = _Connectivity()
        self._raiser = raiser

    async def login(self):
        self.connectivity.can_retry_login = False

    async def request(self, api_request):
        raise self._raiser()


def _client_response_error() -> ClientResponseError:
    """aiohttp's shape: the URL carries the login percent-encoded, and the
    headers carry the API key."""
    from multidict import CIMultiDict, CIMultiDictProxy
    from yarl import URL

    url = URL(f"https://admin:{quote(ESCAPED_SECRET)}@10.0.0.1/proxy/network/api/s/default/set/setting/snmp")
    info = RequestInfo(url, "PUT", CIMultiDictProxy(CIMultiDict({"X-API-KEY": ESCAPED_SECRET})), url)
    return ClientResponseError(info, (), status=401, message=f"Unauthorized for {ESCAPED_SECRET!r}")


def _manager(controller, password=LOGIN_SENTINEL):
    manager = ConnectionManager("192.168.1.1", "admin", password)
    manager.controller = controller
    manager._aiohttp_session = controller.connectivity.config.session
    manager._initialized = True
    manager._auth_generation = 1
    return manager


def _put_with_secret():
    return ApiRequest(
        method="put",
        path="/rest/wlan/wlan-1",
        data={"enabled": True, "x_password": SENTINEL, "nested": {"community": SENTINEL}},
    )


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda: ResponseError(f"controller rejected {{'x_password': '{SENTINEL}'}}"),
        # aiounifi's real shape: ERRORS.get(msg, AiounifiException)(<decoded response dict>)
        lambda: ResponseError(
            {"meta": {"rc": "error", "msg": f"api.err.Invalid {SENTINEL}"}, "data": [{"x_password": SENTINEL}]}
        ),
        lambda: RequestError(f"transport failed while sending x_password={SENTINEL}"),
        lambda: ClientError(f"client error echoing {SENTINEL}"),
        lambda: RuntimeError(f"unexpected: payload {SENTINEL}"),
    ],
    ids=["response_error", "response_error_dict_body", "request_error", "aiohttp_client_error", "unexpected"],
)
async def test_request_write_error_is_scrubbed_before_log_and_reraise(caplog, error_factory):
    manager = _manager(_Controller(error_factory))
    caplog.set_level(logging.DEBUG)

    with pytest.raises(type(error_factory())) as excinfo:
        await manager.request(_put_with_secret())

    assert SENTINEL not in str(excinfo.value)
    assert SENTINEL not in repr(excinfo.value.args)
    assert SENTINEL not in caplog.text
    assert "<redacted>" in str(excinfo.value)
    await manager.cleanup()


async def test_request_read_error_is_scrubbed_of_login_password(caplog):
    """Reads carry no payload, but the login password can still be quoted by the transport."""
    manager = _manager(_Controller(lambda: ResponseError(f"login failed for admin:{LOGIN_SENTINEL}")))
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ResponseError) as excinfo:
        await manager.request(ApiRequest(method="get", path="/stat/sta"))

    assert LOGIN_SENTINEL not in str(excinfo.value)
    assert LOGIN_SENTINEL not in caplog.text
    await manager.cleanup()


async def test_request_scrubs_chained_cause(caplog):
    def _raiser():
        try:
            raise ValueError(f"inner {SENTINEL}")
        except ValueError as inner:
            raise ResponseError("outer") from inner

    manager = _manager(_Controller(_raiser))
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ResponseError) as excinfo:
        await manager.request(_put_with_secret())

    assert SENTINEL not in str(excinfo.value.__cause__)
    assert SENTINEL not in caplog.text
    await manager.cleanup()


async def test_request_scrubs_second_login_required_after_reauth(caplog):
    """The retry branch logs and re-raises its own exception; it must be scrubbed too."""
    manager = _manager(_Controller(lambda: LoginRequired(f"session rejected {SENTINEL}")))
    caplog.set_level(logging.DEBUG)

    with pytest.raises(LoginRequired) as excinfo:
        await manager.request(_put_with_secret())

    assert SENTINEL not in str(excinfo.value)
    assert SENTINEL not in caplog.text
    assert SENTINEL not in (manager.last_connection_error or "")
    await manager.cleanup()


# ---------------------------------------------------------------------------
# SystemManager with a fake connection (the manager must not rely on the
# transport having scrubbed already)
# ---------------------------------------------------------------------------


class _FakeConnection:
    def __init__(self, *, raiser=None, response=None):
        self.site = "default"
        self._raiser = raiser
        self._response = response

    def get_cached(self, key):
        return None

    def _update_cache(self, key, value):
        return None

    def _invalidate_cache(self, key):
        return None

    async def request(self, api_request):
        if api_request.method == "get":
            return [{"_id": "snmp-1", "key": "snmp", "enabled": False}]
        if self._raiser is not None:
            raise self._raiser()
        return self._response


async def test_system_manager_update_exception_is_scrubbed(caplog):
    connection = _FakeConnection(raiser=lambda: ResponseError(f"rejected {{'community': '{SENTINEL}'}}"))
    manager = SystemManager(connection)
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ResponseError) as excinfo:
        await manager.update_settings("snmp", {"enabled": True, "community": SENTINEL})

    assert SENTINEL not in str(excinfo.value)
    assert SENTINEL not in caplog.text


async def test_system_manager_rejected_response_log_is_scrubbed(caplog):
    rejected = {
        "meta": {"rc": "error", "msg": f"api.err.Invalid community={SENTINEL}"},
        "data": [{"community": SENTINEL}],
    }
    connection = _FakeConnection(response=rejected)
    manager = SystemManager(connection)
    caplog.set_level(logging.DEBUG)

    assert await manager.update_settings("snmp", {"enabled": True, "community": SENTINEL}) is False

    assert SENTINEL not in caplog.text
    assert "Error updating snmp settings" in caplog.text


def _assert_private_failure_logs(caplog, operation):
    assert operation in caplog.text
    assert UNKNOWN_SECRET not in caplog.text
    assert SENTINEL not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)
    assert "Traceback (most recent call last)" not in caplog.text


@pytest.mark.parametrize("error_type", [RequestError, RuntimeError, LoginRequired])
async def test_initialize_logs_no_controller_exception_content(caplog, monkeypatch, error_type):
    from unifi_core.network.managers import connection_manager as cm_module

    # Fail inside initialization without creating a real session or contacting a controller.
    def fail_connector(**kwargs):
        raise error_type(UNKNOWN_SECRET)

    monkeypatch.setattr(cm_module.aiohttp, "TCPConnector", fail_connector)
    manager = ConnectionManager("192.168.1.1", "admin", LOGIN_SENTINEL)
    manager._max_retries = 2
    manager._retry_delay = 0
    caplog.set_level(logging.DEBUG)

    assert await manager.initialize() is False
    _assert_private_failure_logs(caplog, "authentication failure" if error_type is LoginRequired else "initializ")
    assert error_type.__name__ in caplog.text
    assert manager.last_connection_error  # Caller diagnostics remain available.
    if error_type is LoginRequired:
        caplog.clear()
        assert await manager.initialize() is False
        _assert_private_failure_logs(caplog, "remains blocked")
    await manager.cleanup()


@pytest.mark.parametrize("error_type", [RequestError, LoginRequired])
async def test_reauthenticate_logs_no_controller_exception_content(caplog, error_type):
    controller = _Controller(lambda: ResponseError("unused"))
    controller.login = AsyncMock(side_effect=error_type(UNKNOWN_SECRET))
    manager = _manager(controller)
    caplog.set_level(logging.DEBUG)

    assert await manager.reauthenticate() is False
    _assert_private_failure_logs(
        caplog, "authentication failure" if error_type is LoginRequired else "re-authentication"
    )
    assert error_type.__name__ in caplog.text
    assert manager.controller is None
    await manager.cleanup()


@pytest.mark.parametrize("handler", ["devices", "clients", "dpi_apps", "dpi_groups"])
@pytest.mark.parametrize("error_type", [LoginRequired, RuntimeError])
async def test_refresh_retry_logs_no_controller_exception_content(caplog, handler, error_type):
    import traceback

    controller = _Controller(lambda: ResponseError("unused"))
    update = AsyncMock(side_effect=error_type(UNKNOWN_SECRET))
    setattr(controller, handler, SimpleNamespace(update=update))
    manager = _manager(controller)
    caplog.set_level(logging.DEBUG)

    with pytest.raises(RequestError) as excinfo:
        await manager.refresh_handler(handler)

    assert update.await_count == (2 if error_type is LoginRequired else 1)
    _assert_private_failure_logs(caplog, "Controller collection refresh failed")
    assert error_type.__name__ in caplog.text
    assert UNKNOWN_SECRET not in str(excinfo.value)
    assert UNKNOWN_SECRET not in "".join(traceback.format_exception(excinfo.value))
    assert manager.reconnect_blocked is (error_type is LoginRequired)
    await manager.cleanup()


async def test_settings_rejection_does_not_log_unrecognized_response_secrets(caplog):
    connection = _FakeConnection(response={"meta": {"rc": "error", "msg": UNKNOWN_SECRET}})
    caplog.set_level(logging.DEBUG)

    assert await SystemManager(connection).update_settings("snmp", {"community": SENTINEL}) is False

    _assert_private_failure_logs(caplog, "Error updating snmp settings")


async def test_settings_exception_does_not_log_opaque_exception_content(caplog):
    class OpaqueError(Exception):
        def __str__(self):
            return f"{SENTINEL} {UNKNOWN_SECRET}"

    connection = _FakeConnection(raiser=OpaqueError)
    caplog.set_level(logging.DEBUG)

    with pytest.raises(OpaqueError):
        await SystemManager(connection).update_settings("snmp", {"community": SENTINEL})

    _assert_private_failure_logs(caplog, "Error updating snmp settings")
    assert "OpaqueError" in caplog.text


# ---------------------------------------------------------------------------
# Encoded representations
#
# The controller error above quotes the payload with ``repr``. When the secret
# itself contains a backslash, quote or newline, its literal form never appears
# in the message — only its escaped form, which decodes straight back.
# ---------------------------------------------------------------------------


async def test_request_write_error_scrubs_escaped_credential(caplog):
    manager = _manager(_Controller(lambda: ResponseError(f"controller rejected {{'x_password': {ESCAPED_SECRET!r}}}")))
    caplog.set_level(logging.DEBUG)
    request = ApiRequest(method="put", path="/rest/wlan/wlan-1", data={"x_password": ESCAPED_SECRET})

    with pytest.raises(ResponseError) as excinfo:
        await manager.request(request)

    assert_unrecoverable(str(excinfo.value), ESCAPED_SECRET)
    assert_unrecoverable(repr(excinfo.value.args), ESCAPED_SECRET)
    assert_unrecoverable(caplog.text, ESCAPED_SECRET)
    await manager.cleanup()


async def test_request_read_error_scrubs_escaped_login_password(caplog):
    manager = _manager(
        _Controller(lambda: ResponseError(f"login failed for {{'password': {ESCAPED_SECRET!r}}}")),
        password=ESCAPED_SECRET,
    )
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ResponseError) as excinfo:
        await manager.request(ApiRequest(method="get", path="/stat/sta"))

    assert_unrecoverable(str(excinfo.value), ESCAPED_SECRET)
    assert_unrecoverable(caplog.text, ESCAPED_SECRET)
    await manager.cleanup()


async def test_recorded_connection_error_scrubs_escaped_password():
    """``_sanitize_text`` masks the configured credential for every connection
    failure it records, and that text is served to later callers through
    ``last_connection_error`` and ``_not_connected_error``."""
    manager = _manager(_Controller(lambda: ResponseError("unused")), password=ESCAPED_SECRET)

    manager._record_connection_error(ResponseError(f"login rejected for admin:{ESCAPED_SECRET!r}"))

    assert_unrecoverable(manager.last_connection_error or "", ESCAPED_SECRET)
    assert_unrecoverable(str(manager._not_connected_error()), ESCAPED_SECRET)
    await manager.cleanup()


async def test_controller_rejection_is_classified_before_the_scrub(caplog):
    """The scrub rewrites the exception in place, so anything that reads the
    message to classify the reply must read it first. A submitted value that
    collides with the controller's error vocabulary must not turn a routine
    negative reply into an unexpected fault."""
    from aiounifi.errors import AiounifiException

    manager = _manager(
        _Controller(lambda: AiounifiException({"meta": {"rc": "error", "msg": "api.err.UnknownUser"}, "data": []}))
    )
    caplog.set_level(logging.DEBUG)

    with pytest.raises(AiounifiException):
        await manager.request(ApiRequest(method="get", path="/stat/user/x", data={"x_password": "err"}))

    assert "Controller rejected request" in caplog.text
    assert "Unexpected error during API request" not in caplog.text
    await manager.cleanup()


async def test_log_sink_scrubs_payload_secret_when_the_exception_ignores_args(caplog):
    """``sanitize_exception`` can only rewrite what the exception exposes. An
    exception whose ``__str__`` ignores ``args`` (pydantic's ValidationError is
    the real one) survives it untouched, so the log sink must scrub the text it
    is about to write rather than trust the mutation."""

    class _Opaque(Exception):
        def __init__(self, text: str) -> None:
            super().__init__()
            self._text = text

        def __str__(self) -> str:
            return self._text

    manager = _manager(_Controller(lambda: _Opaque(f"controller rejected {{'x_password': '{SENTINEL}'}}")))
    caplog.set_level(logging.DEBUG)

    with pytest.raises(_Opaque):
        await manager.request(_put_with_secret())

    assert SENTINEL not in caplog.text
    await manager.cleanup()


async def test_login_required_branch_scrubs_the_exception_it_leaves_as_context(caplog):
    """The re-auth branch does not bind its exception, so the raw
    ``LoginRequired`` — whose ``args[0]`` is the decoded response echoing the
    submitted record — survives as ``__context__`` of the error the caller
    receives, and every ``exc_info=True`` caller renders it in full."""
    import traceback
    from unittest.mock import AsyncMock

    manager = _manager(
        _Controller(
            lambda: LoginRequired(
                {"meta": {"rc": "error", "msg": "api.err.LoginRequired"}, "data": [{"x_password": SENTINEL}]}
            )
        )
    )
    manager._reauthenticate = AsyncMock(return_value=False)
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ConnectionError) as excinfo:
        await manager.request(_put_with_secret())

    rendered = "".join(traceback.format_exception(type(excinfo.value), excinfo.value, excinfo.value.__traceback__))
    assert SENTINEL not in rendered
    assert SENTINEL not in caplog.text
    await manager.cleanup()


async def test_login_is_masked_on_token_boundaries_in_the_reraised_error(caplog):
    """The login is a word ("admin"), so it is masked on token boundaries — the
    same rule the log sink applies. Scrubbing it as a substring would shred the
    message and the durable audit row built from it."""
    manager = _manager(
        _Controller(lambda: ResponseError("PUT /rest/administrator failed: admin-console rejected; user=admin")),
        password="not-in-this-message",
    )
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ResponseError) as excinfo:
        await manager.request(ApiRequest(method="put", path="/rest/x", data={"enabled": True}))

    message = str(excinfo.value)
    assert "administrator" in message
    assert "admin-console" in message
    assert "user=<redacted>" in message
    await manager.cleanup()


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda: RequestError(f"transport failed while sending {ESCAPED_SECRET!r}"),
        lambda: ClientError(f"client error echoing {ESCAPED_SECRET!r}"),
        lambda: _client_response_error(),
    ],
    ids=["request_error", "aiohttp_client_error", "aiohttp_client_response_error"],
)
async def test_transport_error_scrubs_escaped_credential(caplog, error_factory):
    """The maintainer asked for the transport path specifically. aiohttp's
    ``ClientResponseError`` is the hard one: it renders its URL from
    ``request_info``, an attribute aliased to ``args[0]``, so rewriting ``args``
    alone leaves the attribute pointing at the unscrubbed original."""
    import traceback

    manager = _manager(_Controller(error_factory), password=ESCAPED_SECRET)
    caplog.set_level(logging.DEBUG)

    with pytest.raises(Exception) as excinfo:  # noqa: PT011 - three unrelated transport types
        await manager.request(_put_with_secret())

    error = excinfo.value
    assert_unrecoverable(str(error), ESCAPED_SECRET)
    assert_unrecoverable(repr(error.args), ESCAPED_SECRET)
    assert_unrecoverable(repr(getattr(error, "request_info", "")), ESCAPED_SECRET)
    assert_unrecoverable(caplog.text, ESCAPED_SECRET)
    assert_unrecoverable("".join(traceback.format_exception(type(error), error, error.__traceback__)), ESCAPED_SECRET)
    await manager.cleanup()
