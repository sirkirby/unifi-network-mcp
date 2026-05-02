# Release smoke checklist

Manual checks performed before cutting any `api/v*` release tag. Complementary
to `scripts/live_api_smoke.py` — these are visual / judgment items the harness
can't sensibly assert.

The automated harness covers ~30 REST + GraphQL + auth shape assertions across
all three products. This checklist covers the remaining ~10 items that need
human eyeballs.

## Pre-tag (run from a fresh checkout of the release branch)

- [ ] **Service boots cleanly.** `unifi-api-server migrate && unifi-api-server serve` against a fresh state DB; no errors in stdout, no warnings unrelated to known limitations.
- [ ] **Admin UI loads.** Browse `http://localhost:8089/admin/` after login; dashboard renders without console errors.
- [ ] **Theme toggle persists.** Click the theme button, reload, theme persists.
- [ ] **GraphiQL playground loads.** Browse `http://localhost:8089/v1/graphql`; explorer pane shows the full schema with descriptions.
- [ ] **Swagger UI loads.** Browse `http://localhost:8089/v1/docs`; routes are grouped by tag (network/protect/access/admin).
- [ ] **Audit CSV export opens.** Trigger a few mutations through the admin UI, navigate to `/admin/audit`, click Export CSV, open the downloaded file in a spreadsheet app — columns line up, dates parse, no encoding artifacts.
- [ ] **SSE stream visible.** Navigate to `/admin/audit`, click "Live tail", trigger an action via REST, see the new row appear in the audit list within ~1 second.
- [ ] **Live probe works for each product.** Navigate to `/admin/controllers`, click "Probe" on each of network/protect/access; results show ok + reasonable latency.
- [ ] **Read-scope key cannot reach admin endpoints.** Create a read-scope key via CLI; attempt to GET `/v1/diagnostics`; expect 403.
- [ ] **Reference docs are current and accurate.** Open `apps/api/docs/openapi-reference.md` and `apps/api/docs/graphql-reference.md`; spot-check 3 random fields against the live schema in GraphiQL / Swagger UI.

## Automated harness (`scripts/live_api_smoke.py`)

```bash
python scripts/live_api_smoke.py --output /tmp/release-smoke.json
jq '.passed, .failed, .total' /tmp/release-smoke.json
```

Expected: ~30+ passed / 0 failed across network + protect + access. The
harness reads `.env` for controller credentials.

## Post-tag

- [ ] **GitHub Release artifact published.** `gh release view api/v<version>` shows wheel attached and auto-generated notes.
- [ ] **PyPI publish succeeded.** `pip install unifi-api-server==<version>` from a fresh venv succeeds.
- [ ] **Docker image pulled.** `docker pull ghcr.io/sirkirby/unifi-api-server:<version>` succeeds; `docker run` against a fresh state directory boots cleanly.

## Triage protocol

Any failure or unresolved item creates a GitHub issue with `scope:api` + an
appropriate priority label. P1 issues block the tag and get fixed inline.
P2/P3 issues either fold into a hotfix PR before tagging or get scheduled
for the next release per spec §3.5.
