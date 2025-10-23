# Feature Specification: UniFi API Path Detection and Adaptation

**Feature Branch**: `001-unifi-os-detection`
**Created**: 2025-10-23
**Status**: Draft
**Input**: User description: "Automatic detection of required API path structure (proxy vs direct) and URI adjustment for /proxy/network/api path compatibility across UniFi controller variations"

## Clarifications

### Session 2025-10-23

- Q: How should the system integrate with aiounifi library to allow for future native support without breaking changes? → A: Request Path Interceptor - Intercept and modify the path attribute of ApiRequest objects before they're sent
- Q: How frequently should the system re-validate cached controller type detection results? → A: Never re-validate during session
- Q: What should the system do when automatic detection fails completely? → A: Fail Connection with Clear Error - Refuse to connect and require manual override via UNIFI_CONTROLLER_TYPE
- Q: How should the system detect which path structure to use given unpredictable device variations? → A: Empirical probe-based detection - Test both direct `/api` and `/proxy/network/api` paths with a known endpoint and use whichever responds successfully

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic UniFi OS Detection (Priority: P1)

Users deploying the MCP server to newer UniFi controllers (Cloud Gateway, self-hosted UniFi OS 4.x+) experience connection failures with 404 errors because these controllers require `/proxy/network/api` paths instead of the direct `/api` paths that aiounifi constructs. The system should automatically detect which path structure the controller requires by testing both options and using whichever responds successfully, eliminating the need for manual configuration.

**Why this priority**: This is the core functionality that unblocks users on newer controllers. Without this, the MCP server is completely non-functional for these deployments, which represent a growing portion of the user base (issue #19 indicates multiple users affected).

**Independent Test**: Can be fully tested by connecting to a UniFi OS device (UDM-Pro, UXG-Pro, or self-hosted UniFi OS 4.x) and verifying that API calls succeed without manual configuration. Delivers immediate value by making the server functional for UniFi OS users.

**Acceptance Scenarios**:

1. **Given** a controller that requires `/proxy/network/api` paths (e.g., Cloud Gateway, self-hosted UniFi OS), **When** the MCP server initializes, **Then** the system tests both path structures, detects the proxy requirement, and uses `/proxy/network/api` paths for all API requests
2. **Given** a controller that uses direct `/api` paths (e.g., older UniFi OS devices, standalone controllers), **When** the MCP server initializes, **Then** the system tests both path structures, detects direct path support, and uses `/api` paths for all API requests
3. **Given** the connection has been established and path type detected, **When** the server makes any API request, **Then** the correct path structure is applied automatically based on detection result
4. **Given** the detection process tests both path structures, **When** both attempts fail or return errors, **Then** a clear error message is logged indicating the detection failure and providing troubleshooting guidance
5. **Given** a user runs the dev_console.py testing tool, **When** the connection initializes, **Then** the detected path requirement (proxy or direct) is displayed in the console output for verification and debugging purposes

---

### User Story 2 - Manual Override Configuration (Priority: P2)

Some users may need to explicitly force a specific path structure due to network proxies, custom setups, or detection failures. The system should provide an optional configuration setting to override automatic detection.

**Why this priority**: Provides flexibility for edge cases and custom deployments. Not blocking for the majority of users but prevents being locked out when detection fails or behaves unexpectedly.

**Independent Test**: Can be fully tested by setting an environment variable or configuration option (e.g., `UNIFI_CONTROLLER_TYPE=proxy`) and verifying that detection is bypassed and the specified path structure is used. Delivers value by supporting custom deployments.

**Acceptance Scenarios**:

1. **Given** a configuration setting for proxy path requirement (e.g., `UNIFI_CONTROLLER_TYPE=proxy`), **When** the MCP server initializes, **Then** the system skips automatic detection and uses `/proxy/network/api` paths for all requests
2. **Given** a configuration setting for direct paths (e.g., `UNIFI_CONTROLLER_TYPE=direct`), **When** the MCP server initializes, **Then** the system skips automatic detection and uses direct `/api` paths for all requests
3. **Given** an invalid path type is specified in configuration, **When** the MCP server initializes, **Then** the system logs a warning and falls back to automatic detection
4. **Given** no manual override is configured, **When** the MCP server initializes, **Then** the system proceeds with automatic probe-based detection

---

### User Story 3 - Graceful Failure and Retry (Priority: P3)

If the initial detection attempt fails or returns ambiguous results, the system should implement retry logic with exponential backoff, and if all attempts fail, provide a clear error message directing users to configure manual override rather than silently falling back to an incorrect mode.

**Why this priority**: Improves reliability and prevents silent failures. Ensures users get clear guidance when detection fails rather than experiencing confusing 404 errors from an incorrect fallback mode.

**Independent Test**: Can be fully tested by simulating detection failures (network timeout, ambiguous response) and verifying that the system retries appropriately and then fails with actionable error messages. Delivers value by improving robustness and user experience.

**Acceptance Scenarios**:

1. **Given** the initial detection probe times out, **When** the system cannot reach the controller for detection, **Then** the system retries detection up to 3 times with exponential backoff before failing with a clear error message instructing users to set UNIFI_CONTROLLER_TYPE manually
2. **Given** the detection responses are ambiguous or unexpected, **When** both path structures return unrecognized response formats, **Then** the system logs the response details and fails with a clear error message instructing users to set UNIFI_CONTROLLER_TYPE manually
3. **Given** both proxy and direct path probes are tested during detection, **When** neither path structure works (both return errors), **Then** the system raises a clear connection error with diagnostic information and instructions to use manual override configuration
4. **Given** a path requirement has been detected and cached, **When** subsequent API requests occur during the same session, **Then** the system uses the cached path structure without re-validation

---

### Edge Cases

- What happens when a controller's path requirements change after a firmware upgrade? User must restart the MCP service to re-detect the new path structure.
- How does the system handle environments where users switch between different controller types (e.g., migrating from standalone to cloud-hosted)?
- What happens if the detection probe itself returns a 404 (e.g., firewall blocks specific paths)? System treats it as a failed probe and tries the other path structure.
- How does the system behave with future UniFi versions that may introduce new path structures? Probe-based detection should automatically discover new patterns if they respond to test endpoints.
- What happens if the aiounifi library adds native path detection in a future version? The interceptor can be disabled via configuration to defer to library behavior.
- What happens if both path structures return successful responses during detection? System should prefer direct `/api` paths (aiounifi's default behavior) unless manual override specifies otherwise.
- How does the dev_console.py testing tool display detection results to users for troubleshooting? Detected path requirement (proxy/direct) is logged during connection initialization.
- What happens when users run dev_console.py after changing UNIFI_CONTROLLER_TYPE configuration? New value is used immediately, bypassing automatic detection.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically detect which API path structure the controller requires (direct `/api` or proxy `/proxy/network/api`) by testing both patterns with a known endpoint during initial connection
- **FR-002**: System MUST apply the appropriate API path structure based on detection results: `/proxy/network` prefix when proxy is required, no prefix when direct paths work
- **FR-003**: System MUST support manual override via UNIFI_CONTROLLER_TYPE configuration setting with values: `proxy` (force `/proxy/network` prefix), `direct` (force no prefix), or `auto` (default probe-based detection)
- **FR-004**: System MUST log the detected path requirement (proxy or direct) and provide visibility into which probe succeeded for transparency and debugging
- **FR-005**: System MUST handle detection failures gracefully with retry logic (3 attempts with exponential backoff) and if all attempts fail, refuse connection with a clear error message instructing users to set UNIFI_CONTROLLER_TYPE manually
- **FR-006**: System MUST cache the detected path requirement to avoid repeated detection probes on every request
- **FR-007**: System MUST integrate with the existing aiounifi library using a request path interceptor approach that modifies the path attribute of ApiRequest objects before they're sent, allowing for future native support without breaking changes
- **FR-008**: System MUST update the aiounifi dependency to the latest stable version (current: >=83.0.0) before implementing detection
- **FR-009**: System MUST validate detection results by successfully completing at least one test API call with the detected path structure before caching the result
- **FR-010**: System MUST provide clear error messages when detection fails, including: which path structures were tested, specific error responses received from each probe, and explicit instructions to use UNIFI_CONTROLLER_TYPE environment variable for manual override
- **FR-011**: System MUST work seamlessly with the dev_console.py testing tool, displaying detected path requirement during connection initialization
- **FR-012**: System MUST prefer direct `/api` paths when both path structures return successful responses during detection (to maintain aiounifi's default behavior)

### Assumptions

- **A-001**: Path structure requirements (proxy vs direct) cannot be reliably determined by device type or version alone; empirical testing is required
- **A-002**: A controller will consistently accept either direct `/api` paths OR proxy `/proxy/network/api` paths, but the pattern is not predictable across device types or firmware versions
- **A-003**: The detection mechanism can distinguish path requirements by testing a known endpoint with both patterns and observing which returns a successful response
- **A-004**: The aiounifi library currently does not have native path detection or proxy prefix support (as of version 83.0.0)
- **A-005**: Path requirement detection results remain valid for the entire duration of a connection session and are never re-validated automatically (users must restart the service if path requirements change due to firmware upgrade)
- **A-006**: Users have network connectivity to the controller on the standard HTTPS port (443)
- **A-007**: The probe endpoint used for detection will respond consistently regardless of which path structure is tested
- **A-008**: Manual override configuration follows the project's existing configuration precedence (env vars > .env > config.yaml)
- **A-009**: The dev_console.py testing tool uses the same connection manager initialization process as the MCP server, ensuring consistent behavior
- **A-010**: When both path structures return successful responses during detection, preferring direct `/api` paths will not cause functionality issues (as this is aiounifi's existing behavior)

### Key Entities

- **Path Requirement**: An enumeration representing the detected API path structure requirement (Proxy Required, Direct Path, Unknown)
  - Proxy Required: Controller requires `/proxy/network` prefix for all API paths
  - Direct Path: Controller accepts direct `/api` paths without proxy prefix
  - Unknown: Detection failed or both probes returned errors

- **Detection Result**: A cached result containing path requirement, detection timestamp, probe results, and validation status
  - Stored in connection manager state
  - Used to avoid repeated detection probes
  - Includes diagnostic information (which probes succeeded/failed, response codes, error messages)
  - Preference indicator when both paths work (defaults to direct)

- **API Path Interceptor**: A request path modifier that operates on ApiRequest objects before submission
  - Intercepts ApiRequest/ApiRequestV2 objects before they're sent to the controller
  - Applies `/proxy/network` prefix when path requirement is "Proxy Required"
  - Passes through unchanged when path requirement is "Direct Path"
  - Transparent to existing tool implementations
  - Extensible for future path patterns
  - Can be cleanly disabled via configuration if aiounifi adds native path detection

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users connecting to controllers requiring proxy paths (Cloud Gateway, self-hosted UniFi OS) experience zero 404 errors related to API path mismatches without any manual configuration
- **SC-002**: The system successfully detects path requirements within 5 seconds during initial connection
- **SC-003**: 100% of API requests use the correct path structure after successful detection
- **SC-004**: Support tickets related to path mismatch connection failures (issue #19) are reduced to zero
- **SC-005**: The detection mechanism adds no more than 2 seconds to the initial connection time compared to the current implementation
- **SC-006**: Manual override configuration works in 100% of test cases where users explicitly specify path requirement (proxy/direct)
- **SC-007**: The implementation remains compatible when aiounifi library is upgraded to future versions that may include native path detection
- **SC-008**: Error messages during detection failures provide actionable troubleshooting information in 100% of failure scenarios, including which path structures were tested
- **SC-009**: Users can verify correct path requirement detection by running the dev_console.py tool and observing the connection initialization output showing whether proxy or direct paths are being used
- **SC-010**: The system correctly handles controllers where both path structures return successful responses by preferring direct paths (maintaining existing behavior)
