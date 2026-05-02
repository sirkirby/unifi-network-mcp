# Release coverage matrix

Honest record of where each typed resolver gets coverage. Phase 8 introduced
a 3-layer model:

- **Layer 1 — Live smoke** (`scripts/live_api_smoke.py`): real controllers, real data.
- **Layer 2 — Per-resolver fixture e2e** (`apps/api/tests/graphql/fixtures/`): synthetic data, every resolver.
- **Layer 3 — Gap matrix doc** (this file): what's NOT covered, and why.

## Layer 1: live smoke (real controller, real data)

`scripts/live_api_smoke.py` boots `unifi-api-server` in-process and exercises
the configured matrix against real UniFi controllers using credentials from
`.env`. Produces a machine-readable JSON report with ~30 assertions covering
network/protect/access REST + GraphQL + auth + pagination shapes.

**Strengths:** confirms shapes against real-world data. Catches deploy issues
(auth failures, network paths, controller-version drift, real timestamps,
real ID formats).

**Limits:** only exercises resources the controllers HAVE configured. Empty
resources (zero ACL rules, zero traffic routes, zero recordings, zero
visitors) leave the corresponding code paths un-validated by Layer 1.
This is the gap that PR #130 surfaced and Layer 2 closes.

**Resolvers confirmed by Layer 1 in the PR4 final smoke (2026-05-02):** 31/31
assertions passed against all three real controllers (network, protect, access).

REST list endpoints verified (Page envelope shape):
`network/clients`, `network/devices`, `network/networks`, `network/firewall-rules`;
`protect/cameras`, `protect/events`, `protect/recordings`;
`access/doors`, `access/access-devices`, `access/users`, `access/credentials`,
`access/policies`, `access/schedules`, `access/access-events`.

REST detail / non-list endpoints verified:
`network/controllers/{id}` (admin), `network/clients` pagination cursor round-trip,
`protect/cameras/{id}/snapshot` (binary content-type), `protect/health`,
`protect/system-info`.

GraphQL queries verified (no `errors` in response):
`network.clients`, `network.networks`, `network.clients[].device` edge;
`protect.cameras`, `protect.events`, `protect.cameras[].events` edge;
`access.doors`, `access.events`.

Auth scope rejection verified per product (missing-bearer → 401).

**Endpoints intentionally `skipped` by Layer 1 (require elevated proxy permissions
on the test controllers):** `/api/v2/devices/topology4`, `/api/v2/schedules`.
These are covered by Layer 2 fixture tests; their REST shape is asserted there.

## Layer 2: per-resolver fixture e2e tests (synthetic data)

`apps/api/tests/graphql/fixtures/` contains one fixture e2e test per typed
resolver — 122 tests covering every entry in `type_registry._tool_types`,
plus 11 cross-resource edge tests. Each test stubs
`ManagerFactory.get_domain_manager` to return a synthetic fixture list and
asserts the resolver coerces it correctly through `from_manager_output → to_dict`.

**Strengths:** every typed resolver runs cleanly against representative data.
Gate-policed by `test_resolver_coverage` — every entry in `_tool_types` must
have a matching fixture file declaring `# tool: <name>`.

**Limits:** synthetic data; doesn't catch shape drift between fixture and
real-world manager output. (That's Layer 1's job.)

## Layer 3: known coverage gaps

Things explicitly NOT covered by Layers 1 + 2, and the reason:

- **SSE streams under broadcast load.** Layer 1 confirms `text/event-stream`
  content-type and a few audit-row frames. We don't load-test (e.g., 100
  concurrent subscribers); deferred to Phase 9+ if real usage stresses the
  service.
- **Multi-controller failover behaviors.** unifi-api-server supports
  multiple controllers per product. Layer 1 exercises one per product.
  Cross-controller failure modes (one controller offline while siblings
  healthy) aren't smoke-tested.
- **Controller-version compatibility.** Live smoke uses whatever firmware
  the test controllers happen to be on. Older or newer controller firmware
  may surface field-shape differences not caught by either layer.
- **Mutation/action paths.** Phase 6 GraphQL is read-only. Mutation tools
  (`unifi_block_client`, `unifi_lock_door`, etc.) on REST `/v1/actions/*`
  use the legacy `serializer_for_tool()` path and are covered by their own
  per-tool serializer tests, not by Layer 2 fixture tests.
- **Empty-resource paths within Layer 1.** If a real controller has zero
  recordings / zero ACL rules / zero visitors, Layer 1 exercises only the
  list shape (the empty case). The non-empty shape is covered by Layer 2's
  synthetic fixtures, but real-world non-empty data variation can't be
  guaranteed against any specific test controller.
- **Layer 1 endpoints that require elevated permissions.** Some access
  endpoints (`/api/v2/devices/topology4`, `/api/v2/schedules`) require a
  proxy account with elevated scopes. The harness records these as
  `skipped` rather than as hard failures when permission is denied — they
  rely on Layer 2 for shape validation.

## Update protocol

- After each Layer 1 run (PR4 final smoke + post-release runs), update the
  "confirmed by Layer 1" list above.
- After each Layer 2 expansion (resolvers added or rewritten), confirm
  `test_resolver_coverage` stays green.
- When a real-world coverage gap surfaces (live issue, consumer report),
  add it to "known coverage gaps" with a path to closing it.
