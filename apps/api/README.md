# unifi-api

UniFi rich HTTP API service. Provides a non-MCP API surface for desktop apps,
web dashboards, Pi extensions, and other consumers that need streaming, live
feeds, and richer-than-MCP semantics. Depends only on `unifi-core` — does not
depend on the MCP packages.

See `docs/superpowers/specs/2026-04-28-unifi-rich-api-design.md` for the full
design.

## MFA / 2FA support

`unifi-api-server` connects to UniFi controllers using local-account credentials (username + password + optional API token). It does **not** currently support controllers that require MFA / 2FA on local accounts.

If your controller has MFA enabled, you'll need either:
- A separate local account with MFA disabled (recommended for service accounts)
- A long-lived API token (UniFi Network and Protect both support this on recent firmware)

This is the same constraint the MCP servers (`unifi-network-mcp`, `unifi-protect-mcp`, `unifi-access-mcp`) inherit. See issue #150 for context.
