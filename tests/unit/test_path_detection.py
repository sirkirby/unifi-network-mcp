"""Unit tests for UniFi OS path detection functionality.

Tests the proactive detection of controller type (UniFi OS vs Standard)
through empirical endpoint probing.
"""

import asyncio
from typing import Optional
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import aiohttp
from aioresponses import aioresponses

from src.managers.connection_manager import detect_unifi_os_proactively, detect_with_retry, ConnectionManager


class TestPathDetection:
    """Test suite for UniFi OS automatic detection (FR-001, FR-002, FR-003)."""

    @pytest.mark.asyncio
    async def test_detects_unifi_os_correctly(self):
        """Test detection of UniFi OS when proxy endpoint succeeds.

        FR-001: System MUST probe /proxy/network/api/self/sites endpoint
        FR-010: Detection MUST use /api/self/sites endpoint (lightweight)

        Scenario:
        - UniFi OS endpoint (/proxy/network/api/self/sites) returns 200 with valid JSON
        - Standard endpoint should NOT be called (proxy succeeds first)

        Expected: detect_unifi_os_proactively() returns True
        """
        base_url = "https://192.168.1.1:443"

        with aioresponses() as mock:
            # Mock UniFi OS endpoint to succeed
            mock.get(
                f"{base_url}/proxy/network/api/self/sites",
                status=200,
                payload={"meta": {"rc": "ok"}, "data": []}
            )

            async with aiohttp.ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session=session,
                    base_url=base_url,
                    timeout=5
                )

            assert result is True, "Should detect UniFi OS when proxy endpoint succeeds"

    @pytest.mark.asyncio
    async def test_detects_standard_controller(self):
        """Test detection of standard controller when only direct path works.

        FR-001: System MUST probe both endpoints

        Scenario:
        - UniFi OS endpoint (/proxy/network/api/self/sites) fails with 404
        - Standard endpoint (/api/self/sites) returns 200 with valid JSON

        Expected: detect_unifi_os_proactively() returns False
        """
        base_url = "https://192.168.1.1:443"

        with aioresponses() as mock:
            # Mock UniFi OS endpoint to fail
            mock.get(
                f"{base_url}/proxy/network/api/self/sites",
                status=404
            )

            # Mock standard endpoint to succeed
            mock.get(
                f"{base_url}/api/self/sites",
                status=200,
                payload={"meta": {"rc": "ok"}, "data": []}
            )

            async with aiohttp.ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session=session,
                    base_url=base_url,
                    timeout=5
                )

            assert result is False, "Should detect standard controller when only direct path works"

    @pytest.mark.asyncio
    async def test_detection_failure_returns_none(self):
        """Test detection returns None when both endpoints fail.

        Scenario:
        - UniFi OS endpoint fails (404)
        - Standard endpoint fails (404)

        Expected: detect_unifi_os_proactively() returns None (fallback to aiounifi)
        """
        base_url = "https://192.168.1.1:443"

        with aioresponses() as mock:
            # Mock both endpoints to fail
            mock.get(
                f"{base_url}/proxy/network/api/self/sites",
                status=404
            )

            mock.get(
                f"{base_url}/api/self/sites",
                status=404
            )

            async with aiohttp.ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session=session,
                    base_url=base_url,
                    timeout=5
                )

            assert result is None, "Should return None when both endpoints fail"

    @pytest.mark.asyncio
    async def test_both_paths_succeed_prefers_direct(self):
        """Test that when both paths succeed, detection prefers direct (FR-012).

        FR-012: If both paths succeed (ambiguous), system MUST prefer direct paths

        Scenario:
        - Both UniFi OS and standard endpoints return 200 with valid JSON

        Expected: detect_unifi_os_proactively() returns False (prefers direct)
        """
        base_url = "https://192.168.1.1:443"

        with aioresponses() as mock:
            # Mock both endpoints to succeed
            mock.get(
                f"{base_url}/proxy/network/api/self/sites",
                status=200,
                payload={"meta": {"rc": "ok"}, "data": []}
            )

            mock.get(
                f"{base_url}/api/self/sites",
                status=200,
                payload={"meta": {"rc": "ok"}, "data": []}
            )

            async with aiohttp.ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session=session,
                    base_url=base_url,
                    timeout=5
                )

            assert result is False, "Should prefer direct path when both succeed (FR-012)"

    @pytest.mark.asyncio
    async def test_detection_timeout_handling(self):
        """Test that detection handles timeouts gracefully (SC-002, SC-005).

        SC-002: Detection must complete within 5 seconds
        SC-005: Detection adds ≤2 seconds to connection time

        Scenario:
        - GET requests raise asyncio.TimeoutError

        Expected: detect_unifi_os_proactively() returns None
        """
        base_url = "https://192.168.1.1:443"

        with aioresponses() as mock:
            # Mock timeout on UniFi OS endpoint
            mock.get(
                f"{base_url}/proxy/network/api/self/sites",
                exception=asyncio.TimeoutError("Request timeout")
            )

            # Mock timeout on standard endpoint
            mock.get(
                f"{base_url}/api/self/sites",
                exception=asyncio.TimeoutError("Request timeout")
            )

            async with aiohttp.ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session=session,
                    base_url=base_url,
                    timeout=5
                )

            assert result is None, "Should return None when requests timeout"

    @pytest.mark.asyncio
    async def test_detection_retries_with_exponential_backoff(self):
        """Test retry logic with exponential backoff delays (FR-008).

        FR-008: System MUST retry detection up to 3 times with exponential backoff (1s, 2s, 4s)

        Scenario:
        - First 2 attempts: Both endpoints fail (exception)
        - Third attempt: Standard endpoint succeeds (200)

        Expected:
        - Detection function called 3 times
        - Returns False (standard controller detected on 3rd try)
        - Exponential backoff delays observed (1s, 2s)
        """
        base_url = "https://192.168.1.1:443"
        call_count = 0

        async def mock_detect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # First 2 attempts fail
                raise aiohttp.ClientError("Connection error")
            else:
                # Third attempt succeeds - standard controller
                return False

        async with aiohttp.ClientSession() as session:
            with patch('src.managers.connection_manager.detect_unifi_os_proactively', side_effect=mock_detect):
                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    result = await detect_with_retry(session, base_url, max_retries=3, timeout=5)

                    # Verify result
                    assert result is False, "Should detect standard controller on 3rd attempt"
                    assert call_count == 3, "Should call detection function 3 times"

                    # Verify exponential backoff delays
                    assert mock_sleep.call_count == 2, "Should sleep twice (after 1st and 2nd failures)"
                    sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
                    assert sleep_calls == [1, 2], "Should use exponential backoff: 1s, 2s"

    @pytest.mark.asyncio
    async def test_detection_timeout_retries_then_fails(self):
        """Test that timeouts are retried and eventually fail gracefully (FR-008, FR-009).

        FR-008: System MUST retry detection up to 3 times
        FR-009: System MUST provide clear, actionable error messages

        Scenario:
        - All 3 attempts: Raise asyncio.TimeoutError

        Expected:
        - Detection function called 3 times
        - Returns None (fallback to aiounifi)
        - No exceptions raised (graceful failure)
        """
        base_url = "https://192.168.1.1:443"
        call_count = 0

        async def mock_detect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("Request timeout")

        async with aiohttp.ClientSession() as session:
            with patch('src.managers.connection_manager.detect_unifi_os_proactively', side_effect=mock_detect):
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    result = await detect_with_retry(session, base_url, max_retries=3, timeout=5)

                    # Verify graceful failure
                    assert result is None, "Should return None after all retries fail"
                    assert call_count == 3, "Should attempt detection 3 times"

    @pytest.mark.asyncio
    async def test_detection_result_cached_for_session(self):
        """Test that detection only runs once per session (FR-011).

        FR-011: Detection result MUST be cached and MUST NOT re-run during session lifetime

        Scenario:
        - Create ConnectionManager
        - Call initialize() twice

        Expected:
        - Detection function called only ONCE (first initialization)
        - Second initialization skips detection (uses cached result)
        """
        detection_call_count = 0

        async def mock_detect(*args, **kwargs):
            nonlocal detection_call_count
            detection_call_count += 1
            return True  # Simulate UniFi OS detection

        # Create connection manager
        manager = ConnectionManager(
            host="192.168.1.1",
            username="test_user",
            password="test_pass",
            port=443,
            site="default"
        )

        # Mock the Controller and login
        mock_controller = MagicMock()
        mock_controller.login = AsyncMock()
        mock_controller.connectivity = MagicMock()
        mock_controller.connectivity.is_unifi_os = False

        with patch('src.managers.connection_manager.detect_with_retry', side_effect=mock_detect):
            with patch('src.managers.connection_manager.Controller', return_value=mock_controller):
                with patch('src.bootstrap.UNIFI_CONTROLLER_TYPE', 'auto'):
                    # First initialization
                    result1 = await manager.initialize()
                    first_call_count = detection_call_count

                    # Verify first initialization succeeded
                    assert result1 is True, "First initialization should succeed"
                    assert first_call_count == 1, "Detection should run on first initialization"
                    assert manager._unifi_os_override is True, "Detection result should be cached"

                    # Reset initialized flag to force re-initialization logic
                    manager._initialized = False
                    if manager._aiohttp_session and not manager._aiohttp_session.closed:
                        await manager._aiohttp_session.close()

                    # Second initialization - should use cached result
                    result2 = await manager.initialize()
                    second_call_count = detection_call_count

                    # Verify detection was cached (only called once)
                    assert result2 is True, "Second initialization should succeed"
                    assert second_call_count == 1, "Detection should NOT run on second initialization (cached)"
                    assert manager._unifi_os_override is True, "Cached result should be preserved"

        # Cleanup
        await manager.cleanup()
