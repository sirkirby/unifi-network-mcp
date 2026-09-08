# Network connection and settings logging alerts

Reviewed GitHub's eight open CodeQL alerts on main commit
`860809ffa912312c978c764e72d584e348491fed` on 2026-09-07. All use
`py/clear-text-logging-sensitive-data` (high severity).

The flagged values pass through custom sanitizers, but these are not a complete
privacy boundary for logs. Configured/submitted credential matching cannot cover
controller-only secrets in arbitrary exception text or response messages. Runtime
tests reproduced leaks using a controller-only sentinel. An adjacent settings
exception log also leaked a submitted credential when the exception's `__str__`
ignored its rewritten `args`.

| Alert | Location at reviewed main | Disposition |
| --- | --- | --- |
| [72](https://github.com/sirkirby/unifi-mcp/security/code-scanning/72) | `connection_manager.py:478` | Log terminal authentication exception class and cooldown, omitting exception text. |
| [73](https://github.com/sirkirby/unifi-mcp/security/code-scanning/73) | `connection_manager.py:583` | Log fixed blocked-reconnect context, omitting cached error text. |
| [74](https://github.com/sirkirby/unifi-mcp/security/code-scanning/74) | `connection_manager.py:716` | Log attempt number and exception class. |
| [75](https://github.com/sirkirby/unifi-mcp/security/code-scanning/75) | `connection_manager.py:724` | Log exhausted attempt count and exception class. |
| [76](https://github.com/sirkirby/unifi-mcp/security/code-scanning/76) | `connection_manager.py:735` | Log initialization failure context and exception class. |
| [77](https://github.com/sirkirby/unifi-mcp/security/code-scanning/77) | `connection_manager.py:795` | Log reauthentication failure context and exception class. |
| [78](https://github.com/sirkirby/unifi-mcp/security/code-scanning/78) | `connection_manager.py:864` | Log refresh failure context and exception class. |
| [79](https://github.com/sirkirby/unifi-mcp/security/code-scanning/79) | `system_manager.py:333` | Omit rejected response bodies; adjacent exception handler logs exception class. |

This follows the existing Network client/device logging pattern. Request-error
scrubbing, response redaction policy, authentication classification,
reconnect circuit, and retry behavior remain intact. No tools or public schemas
are added or changed. Auto-backup read/preview/update and DPI MCP error responses
now include the exception class instead of exception text. Their manager/tool
caller chains also omit exception messages and tracebacks, so re-raising cannot
reintroduce sensitive content at those downstream logs. This is a focused
remediation of the listed logging boundaries, not a
claim that every log or caller-facing exception is free of arbitrary secrets.

Cached connection failures now contain exception class and fixed remediation
guidance, so later tool calls cannot log cached controller text. Failed
reauthentication also suppresses the original LoginRequired traceback context.
Settings failure logging omits controller text inside ConnectionManager, which
then translates the failure into a new RequestError containing fixed context
and the original exception class. Original traceback context is suppressed.
This protects every settings caller, including management/site/gateway tools
that log exceptions. Other request error types and logging retain their existing
behavior.

DPI refresh failures also become safe RequestError instances at StatsManager,
with original traceback context suppressed. REST and GraphQL use this manager
directly, so the safe error must be established before the MCP boundary.
ConnectionManager applies safe RequestError translation to all handler refresh
failures after authentication/circuit handling, protecting client and device
callers as well as DPI callers.

Validation: eight new behavioral regression cases failed before the fix and
passed afterward; 54 focused credential sanitization, request logging, and
reauthentication tests passed. Caller-chain regressions exercise real connection
and domain managers: auto-backup read, preview, update fetch and update PUT with
opaque, request and response exceptions; both DPI handlers; and tool calls after
failed initialization or reauthentication; and management/site/gateway settings
callers that log tracebacks. REST and GraphQL DPI regressions exercise both
handlers through the real manager/connection chain. Full repository and GitHub scan results are
recorded in the associated pull request. Alert closure on main requires the
change to be merged and scanned; no alerts were manually dismissed.
