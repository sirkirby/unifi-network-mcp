# Quickstart: UniFi OS Path Detection Implementation

**Feature**: UniFi API Path Detection and Adaptation
**Branch**: 001-unifi-os-detection
**Date**: 2025-10-23
**Target Audience**: Developers implementing this feature

## Overview

This quickstart guide provides step-by-step instructions for implementing the UniFi OS path detection feature. Follow these steps in order to minimize integration issues and ensure comprehensive testing.

**Estimated Time**: 4-6 hours for complete implementation and testing

---

## Prerequisites

Before starting implementation:

- [ ] Read `spec.md` (feature specification)
- [ ] Read `research.md` (technical research findings)
- [ ] Read `data-model.md` (data structures)
- [ ] Review `contracts/detection-api.md` (API contracts)
- [ ] Have access to both UniFi OS and standard controller for testing

**Development Environment**:
- Python 3.13+
- aiounifi >= 83.0.0
- aiohttp >= 3.8.5
- pytest with pytest-asyncio

---

## Phase 1: Detection Logic (30 minutes)

### Step 1.1: Add Detection Method

Edit `src/managers/connection_manager.py`:

```python
import asyncio
import aiohttp
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Add this method to ConnectionManager class
async def detect_unifi_os_proactively(
    session: aiohttp.ClientSession,
    base_url: str,
    timeout: int = 5
) -> Optional[bool]:
    """
    Detect if controller is UniFi OS by testing endpoint variants.

    Args:
        session: Active aiohttp.ClientSession
        base_url: Base URL of controller (e.g., 'https://192.168.1.1:443')
        timeout: Detection timeout in seconds

    Returns:
        True: UniFi OS detected (requires /proxy/network prefix)
        False: Standard controller detected (uses /api paths)
        None: Detection failed, fall back to aiounifi's check_unifi_os()
    """
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    # Try UniFi OS endpoint first
    try:
        async with session.get(
            f"{base_url}/proxy/network/api/self/sites",
            ssl=False,
            timeout=client_timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "data" in data:
                    logger.info("Detected UniFi OS controller (proxy paths required)")
                    return True
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.debug(f"UniFi OS endpoint probe failed: {e}")

    # Try standard endpoint
    try:
        async with session.get(
            f"{base_url}/api/self/sites",
            ssl=False,
            timeout=client_timeout
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if "data" in data:
                    logger.info("Detected standard controller (direct /api paths)")
                    return False
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.debug(f"Standard endpoint probe failed: {e}")

    logger.warning("Path detection failed, falling back to aiounifi's check_unifi_os()")
    return None
```

**Test**:

```bash
# Create a simple test script
python -c "
import asyncio
import aiohttp
from src.managers.connection_manager import detect_unifi_os_proactively

async def test():
    async with aiohttp.ClientSession() as session:
        result = await detect_unifi_os_proactively(
            session,
            'https://your-controller:443'
        )
        print(f'Detection result: {result}')

asyncio.run(test())
"
```

---

## Phase 2: Configuration (15 minutes)

### Step 2.1: Add Configuration Constant

Edit `src/bootstrap.py`:

```python
# Add to imports
import os

# Add constant
UNIFI_CONTROLLER_TYPE = os.getenv("UNIFI_CONTROLLER_TYPE", "auto").lower()

# Add validation
VALID_CONTROLLER_TYPES = {"auto", "proxy", "direct"}

if UNIFI_CONTROLLER_TYPE not in VALID_CONTROLLER_TYPES:
    logger.warning(
        f"Invalid UNIFI_CONTROLLER_TYPE: '{UNIFI_CONTROLLER_TYPE}'. "
        f"Must be one of: {', '.join(VALID_CONTROLLER_TYPES)}. "
        f"Defaulting to 'auto'."
    )
    UNIFI_CONTROLLER_TYPE = "auto"
```

### Step 2.2: Update config.yaml (Optional)

Edit `src/config/config.yaml`:

```yaml
# Add new section
unifi:
  # Existing settings...

  # NEW: Controller type configuration
  controller_type: auto  # auto | proxy | direct
  # auto: Automatically detect (default)
  # proxy: Force UniFi OS paths (/proxy/network prefix)
  # direct: Force standard paths (/api)
```

**Test**:

```bash
# Test environment variable
export UNIFI_CONTROLLER_TYPE=proxy
python -m src.bootstrap  # Should load without errors

# Test invalid value
export UNIFI_CONTROLLER_TYPE=invalid
python -m src.bootstrap  # Should show warning and default to auto
```

---

## Phase 3: Connection Manager Integration (45 minutes)

### Step 3.1: Add State Attributes

Edit `src/managers/connection_manager.py` `__init__` method:

```python
def __init__(self, ...):
    # Existing attributes...

    # NEW: Path detection state
    self._unifi_os_override: Optional[bool] = None
    """
    Override for is_unifi_os flag:
    - None: Use aiounifi's detection (no override)
    - True: Force UniFi OS paths (/proxy/network)
    - False: Force standard paths (/api)
    """
```

### Step 3.2: Modify `initialize()` Method

Edit `src/managers/connection_manager.py`:

```python
async def initialize(self) -> bool:
    """Initialize controller connection with path detection."""

    # ... existing session creation code ...

    # NEW: Path detection logic
    from src.bootstrap import UNIFI_CONTROLLER_TYPE

    if UNIFI_CONTROLLER_TYPE == "proxy":
        self._unifi_os_override = True
        logger.info("Controller type forced to UniFi OS (proxy) via config")
    elif UNIFI_CONTROLLER_TYPE == "direct":
        self._unifi_os_override = False
        logger.info("Controller type forced to standard (direct) via config")
    elif UNIFI_CONTROLLER_TYPE == "auto":
        # Proactive detection
        detected = await detect_unifi_os_proactively(
            self._aiohttp_session,
            self.url_base,
            timeout=5
        )
        if detected is not None:
            self._unifi_os_override = detected
            mode = "UniFi OS (proxy)" if detected else "standard (direct)"
            logger.info(f"Auto-detected controller type: {mode}")
        else:
            logger.warning("Auto-detection failed, using aiounifi's check_unifi_os()")

    # ... rest of existing code (Controller creation, login, etc.) ...
```

### Step 3.3: Modify `request()` Method

Edit `src/managers/connection_manager.py`:

```python
async def request(
    self,
    api_request: ApiRequest | ApiRequestV2,
    return_raw: bool = False
) -> Any:
    """Make request with optional path interception."""

    if not await self.ensure_connected() or not self.controller:
        raise ConnectionError("Unifi Controller is not connected.")

    # NEW: Apply override if we have better detection
    original_is_unifi_os = None
    if self._unifi_os_override is not None:
        original_is_unifi_os = self.controller.connectivity.is_unifi_os
        if original_is_unifi_os != self._unifi_os_override:
            logger.debug(
                f"Overriding is_unifi_os from {original_is_unifi_os} "
                f"to {self._unifi_os_override} for this request"
            )
            self.controller.connectivity.is_unifi_os = self._unifi_os_override

    try:
        # Existing request logic
        request_method = (
            self.controller.connectivity._request
            if return_raw
            else self.controller.request
        )
        response = await request_method(api_request)
        return response if return_raw else response.get("data")
    finally:
        # NEW: Always restore original value
        if original_is_unifi_os is not None:
            self.controller.connectivity.is_unifi_os = original_is_unifi_os
```

**Test**:

```bash
# Test with real controller
export UNIFI_HOST=your-controller
export UNIFI_USERNAME=admin
export UNIFI_PASSWORD=password
export UNIFI_CONTROLLER_TYPE=auto

# Run dev console
python devtools/dev_console.py

# Should see detection logs and successful connection
```

---

## Phase 4: Testing (90 minutes)

### Step 4.1: Unit Tests

Create `tests/unit/test_path_detection.py`:

```python
import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from src.managers.connection_manager import detect_unifi_os_proactively


@pytest.mark.asyncio
class TestPathDetection:
    """Unit tests for path detection logic."""

    async def test_detects_unifi_os_correctly(self):
        """Test UniFi OS detection succeeds."""
        with aioresponses() as mock:
            mock.get(
                'https://controller:443/proxy/network/api/self/sites',
                status=200,
                payload={'meta': {'rc': 'ok'}, 'data': []}
            )

            async with ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session,
                    'https://controller:443'
                )

            assert result is True

    async def test_detects_standard_controller(self):
        """Test standard controller detection succeeds."""
        with aioresponses() as mock:
            # UniFi OS path fails
            mock.get(
                'https://controller:443/proxy/network/api/self/sites',
                status=404
            )
            # Standard path succeeds
            mock.get(
                'https://controller:443/api/self/sites',
                status=200,
                payload={'meta': {'rc': 'ok'}, 'data': []}
            )

            async with ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session,
                    'https://controller:443'
                )

            assert result is False

    async def test_detection_failure_returns_none(self):
        """Test detection failure returns None."""
        with aioresponses() as mock:
            # Both endpoints fail
            mock.get(
                'https://controller:443/proxy/network/api/self/sites',
                status=404
            )
            mock.get(
                'https://controller:443/api/self/sites',
                status=404
            )

            async with ClientSession() as session:
                result = await detect_unifi_os_proactively(
                    session,
                    'https://controller:443'
                )

            assert result is None
```

Run tests:

```bash
pytest tests/unit/test_path_detection.py -v
```

### Step 4.2: Integration Tests

Create `tests/integration/test_path_interceptor.py`:

```python
import pytest
from aioresponses import aioresponses
from src.managers.connection_manager import ConnectionManager
from aiounifi.models.client import ClientListRequest


@pytest.mark.asyncio
class TestPathInterceptor:
    """Integration tests for path interception."""

    async def test_path_interception_applies_correctly(self):
        """Test that path interception modifies requests."""
        # Setup ConnectionManager with forced UniFi OS mode
        conn_mgr = ConnectionManager(
            host="controller",
            username="admin",
            password="password"
        )
        conn_mgr._unifi_os_override = True  # Force UniFi OS mode

        with aioresponses() as mock:
            # Mock the intercepted path
            mock.get(
                'https://controller:443/proxy/network/api/s/default/stat/sta',
                payload={'meta': {'rc': 'ok'}, 'data': []}
            )

            await conn_mgr.initialize()
            clients = await conn_mgr.request(ClientListRequest.create())

            # Verify intercepted path was called
            assert len(mock.requests) > 0
            assert '/proxy/network/' in str(mock.requests)
```

Run tests:

```bash
pytest tests/integration/test_path_interceptor.py -v
```

### Step 4.3: Manual Testing

1. **Test with UniFi OS controller** (Cloud Gateway, UDM-Pro):

```bash
export UNIFI_CONTROLLER_TYPE=auto
export UNIFI_HOST=your-udm-pro
python devtools/dev_console.py

# Expected: "Detected UniFi OS controller (proxy paths required)"
# Expected: Successful API calls to /proxy/network/api/* paths
```

2. **Test with standard controller**:

```bash
export UNIFI_CONTROLLER_TYPE=auto
export UNIFI_HOST=your-standalone-controller
python devtools/dev_console.py

# Expected: "Detected standard controller (direct /api paths)"
# Expected: Successful API calls to /api/* paths
```

3. **Test manual override**:

```bash
# Force proxy mode
export UNIFI_CONTROLLER_TYPE=proxy
python devtools/dev_console.py

# Expected: "Controller type forced to UniFi OS (proxy) via config"

# Force direct mode
export UNIFI_CONTROLLER_TYPE=direct
python devtools/dev_console.py

# Expected: "Controller type forced to standard (direct) via config"
```

---

## Phase 5: Diagnostics & Logging (30 minutes)

### Step 5.1: Update dev_console.py

Edit `devtools/dev_console.py`:

```python
async def main():
    # ... existing code ...

    # NEW: Display detection result
    if hasattr(conn_mgr, '_unifi_os_override'):
        if conn_mgr._unifi_os_override is True:
            print("✓ Controller Type: UniFi OS (proxy paths)")
        elif conn_mgr._unifi_os_override is False:
            print("✓ Controller Type: Standard (direct paths)")
        else:
            print("⚠ Controller Type: Using aiounifi auto-detection")

    # ... rest of existing code ...
```

### Step 5.2: Add Diagnostics Logging

If `diagnostics.py` exists, add detection logging:

```python
def log_detection_result(
    requires_proxy: bool,
    detection_method: str,
    duration_ms: float
):
    """Log detection result for diagnostics."""
    mode = "UniFi OS (proxy)" if requires_proxy else "Standard (direct)"
    logger.info(
        f"Detection complete: {mode} via {detection_method} "
        f"in {duration_ms:.0f}ms"
    )
```

---

## Phase 6: Error Handling (20 minutes)

### Step 6.1: Add Retry Logic

Enhance `detect_unifi_os_proactively()` with retries:

```python
async def detect_with_retry(
    session: aiohttp.ClientSession,
    base_url: str,
    max_retries: int = 3
) -> Optional[bool]:
    """Detect with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            result = await detect_unifi_os_proactively(session, base_url)
            if result is not None:
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # 1s, 2s, 4s
                logger.debug(f"Detection attempt {attempt+1} failed, retrying in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Detection failed after {max_retries} attempts")

    return None
```

### Step 6.2: Add Clear Error Messages

```python
if result is None:
    error_msg = f"""
UniFi controller path detection failed.

Troubleshooting:
1. Verify network connectivity to {base_url}
2. Check controller is accessible on port {port}
3. Manually set controller type:
   - For UniFi OS: export UNIFI_CONTROLLER_TYPE=proxy
   - For standalone: export UNIFI_CONTROLLER_TYPE=direct

For more help: https://github.com/sirkirby/unifi-network-mcp/issues/19
"""
    logger.warning(error_msg)
```

---

## Phase 7: Documentation (15 minutes)

### Step 7.1: Update README.md

Add configuration section:

```markdown
## Configuration

### Controller Type Detection

The MCP server automatically detects whether your UniFi controller requires
proxy paths (UniFi OS) or direct paths (standalone).

#### Automatic Detection (Default)

```bash
# No configuration needed - detection happens automatically
UNIFI_CONTROLLER_TYPE=auto  # or omit entirely
```

#### Manual Override

If automatic detection fails or you want to force a specific mode:

```bash
# For UniFi OS (Cloud Gateway, UDM-Pro, self-hosted UniFi OS)
export UNIFI_CONTROLLER_TYPE=proxy

# For standalone controllers
export UNIFI_CONTROLLER_TYPE=direct
```

#### Troubleshooting

If you see connection errors:
1. Check `UNIFI_CONTROLLER_TYPE` setting
2. Try manual override
3. See [Issue #19](https://github.com/sirkirby/unifi-network-mcp/issues/19)
```

---

## Phase 8: Validation (30 minutes)

### Validation Checklist

- [ ] **Detection works on UniFi OS controller**
  - Test with Cloud Gateway or UDM-Pro
  - Verify logs show "Detected UniFi OS controller"
  - Verify API calls succeed

- [ ] **Detection works on standard controller**
  - Test with standalone UniFi controller
  - Verify logs show "Detected standard controller"
  - Verify API calls succeed

- [ ] **Manual override works**
  - Test `UNIFI_CONTROLLER_TYPE=proxy`
  - Test `UNIFI_CONTROLLER_TYPE=direct`
  - Verify logs show "forced to ... via config"

- [ ] **Detection failure handled gracefully**
  - Simulate offline controller
  - Verify fallback to aiounifi works
  - Verify clear error messages

- [ ] **Performance within targets**
  - Detection completes in <5s
  - Detection adds <2s to connection time
  - No overhead on subsequent requests

- [ ] **All tools work without modification**
  - Test existing MCP tools
  - Verify transparent operation
  - No breaking changes

- [ ] **Unit tests pass**
  - `pytest tests/unit/test_path_detection.py`
  - Coverage >90%

- [ ] **Integration tests pass**
  - `pytest tests/integration/test_path_interceptor.py`
  - Test both controller types

---

## Common Issues & Solutions

### Issue 1: Detection Always Fails

**Symptom**: Both probes return 404 or timeout

**Solutions**:
1. Check network connectivity: `ping your-controller`
2. Verify SSL settings: Try `verify_ssl: false`
3. Check firewall rules
4. Use manual override as workaround

### Issue 2: Wrong Path Type Detected

**Symptom**: Detection succeeds but API calls fail with 404

**Solutions**:
1. Use manual override: `UNIFI_CONTROLLER_TYPE=proxy` or `direct`
2. Check controller firmware version
3. Report issue with diagnostic logs

### Issue 3: Slow Connection Initialization

**Symptom**: Connection takes >5 seconds

**Solutions**:
1. Reduce detection timeout: Add `timeout=2` parameter
2. Use manual override to skip detection
3. Check network latency

---

## Next Steps

After completing implementation:

1. **Create pull request** with changes
2. **Update CHANGELOG** with new feature
3. **Close issue #19** (UniFi OS path errors)
4. **Monitor** for detection accuracy issues
5. **Gather metrics** on detection success rate

---

## Reference

**Related Documents**:
- [Feature Specification](./spec.md) - Requirements and acceptance criteria
- [Research](./research.md) - Technical research findings
- [Data Model](./data-model.md) - Data structures and state management
- [API Contracts](./contracts/detection-api.md) - API contracts and behavior
- [Implementation Plan](./plan.md) - High-level implementation strategy

**External Resources**:
- [aiounifi GitHub](https://github.com/Kane610/aiounifi)
- [UniFi API Documentation](https://ubntwiki.com/products/software/unifi-controller/api)
- [Issue #19](https://github.com/sirkirby/unifi-network-mcp/issues/19)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Estimated Completion Time**: 4-6 hours
