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

This follows the existing Network client/device logging pattern. Caller-facing
error scrubbing, response redaction policy, authentication classification,
reconnect circuit, and retry behavior remain intact. No tools or public schemas
change. This is a focused remediation of the listed logging boundaries, not a
claim that every log or caller-facing exception is free of arbitrary secrets.

Validation: eight new behavioral regression cases failed before the fix and
passed afterward; 54 focused credential sanitization, request logging, and
reauthentication tests passed. Full repository and GitHub scan results are
recorded in the associated pull request. Alert closure on main requires the
change to be merged and scanned; no alerts were manually dismissed.
