# unifi-api-server

REST + GraphQL HTTP API for UniFi controllers — a standalone HTTP service for
desktop apps, web dashboards, Pi extensions, and any consumer that wants typed
read access to UniFi Network, Protect, and Access without speaking MCP.

## Quick start

```bash
docker run -d \
  --name unifi-api-server \
  -p 8080:8080 \
  -e UNIFI_API_DB_KEY=$(openssl rand -hex 32) \
  -v unifi-api-state:/var/lib/unifi-api \
  ghcr.io/sirkirby/unifi-api-server:latest

# Save the admin key shown in the logs.
docker logs unifi-api-server | grep "Initial admin API key"
```

Once running:
- REST playground: <http://localhost:8080/v1/docs>
- GraphQL playground: <http://localhost:8080/v1/graphql>
- OpenAPI spec: <http://localhost:8080/v1/openapi.json>
- Health: <http://localhost:8080/v1/health>

First GraphQL query:

```bash
curl -s http://localhost:8080/v1/graphql \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ network { clients(controller: \"<id>\") { items { mac hostname } } } }"}'
```

You can register controllers via the admin UI at `/admin/` or the REST endpoint
`POST /v1/controllers` once you have the admin key.

## Architecture

`unifi-api-server` is a **standalone HTTP service**. It runs independently of the
MCP servers — both projects share the same manager packages from `unifi-core`,
but neither depends on the other being running. Choose based on the consumer:

- **Hobbyist with Claude Code:** run only the MCP servers; skip `unifi-api-server`.
- **App developer building on the API:** run only `unifi-api-server` via Docker.
- **Tool builder who wants both:** run both as parallel containers (see
  [`docs/docker-compose.example.yml`](docs/docker-compose.example.yml)).

The HTTP layer is FastAPI; GraphQL is Strawberry on top of the same projection
types REST uses, so consumer-facing field names are identical across the two
surfaces. Pagination is cursor-based on REST, slice-based on GraphQL.

## Distribution

`unifi-api-server` is published to:

- **PyPI:** `pip install unifi-api-server`
- **GHCR:** `docker pull ghcr.io/sirkirby/unifi-api-server:latest`
- **GitHub Releases:** wheels attached to each `api/v*` tag

The distribution name `unifi-api-server` establishes `unifi-api-*` as the family
namespace for the API and its future ecosystem (planned: `unifi-api-python-sdk`,
`unifi-api-ts-sdk`, `unifi-api-cli`). The import name remains `unifi_api`.

## Configuration

Two layers — environment variables override `config.yaml`. Defaults work for a
standard local install; override only what you need.

| Variable | Default | Purpose |
|---|---|---|
| `UNIFI_API_DB_KEY` | _(required)_ | Encrypts controller credentials in the state DB. Generate once: `openssl rand -hex 32` |
| `UNIFI_API_STATE_DIR` | `/var/lib/unifi-api` | Where the SQLite state DB lives |
| `UNIFI_API_HTTP_HOST` | `127.0.0.1` | Bind address (set to `0.0.0.0` for non-localhost access) |
| `UNIFI_API_HTTP_PORT` | `8080` | Listen port |
| `UNIFI_API_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

Per-controller credentials are stored encrypted in the state DB after the first
`POST /v1/controllers` call — no controller credentials in env vars.

## MFA / 2FA support

`unifi-api-server` connects to UniFi controllers using local-account credentials
(username + password + optional API token). It does **not** currently support
controllers that require MFA / 2FA on local accounts.

If your controller has MFA enabled, you'll need either:
- A separate local account with MFA disabled (recommended for service accounts)
- A long-lived API token (UniFi Network and Protect both support this on recent
  firmware)

This is the same constraint the MCP servers (`unifi-network-mcp`,
`unifi-protect-mcp`, `unifi-access-mcp`) inherit. See issue #150 for context.

## Documentation

- **Reference docs** are auto-generated and drift-gated. Browse them in-repo or
  via the live exploration UIs:
  - [REST OpenAPI spec (JSON)](openapi.json)
  - [REST reference (markdown)](docs/openapi-reference.md)
  - [GraphQL SDL](src/unifi_api/graphql/schema.graphql)
  - [GraphQL reference (markdown)](docs/graphql-reference.md)
  - **Live exploration:** Swagger UI at `/v1/docs`, GraphiQL at `/v1/graphql`
- [`docs/README.md`](docs/README.md) — index linking all artifacts plus
  deployment patterns
- [`docs/release-smoke-checklist.md`](docs/release-smoke-checklist.md) — manual
  release smoke checks
- [`docs/release-coverage.md`](docs/release-coverage.md) — coverage matrix
  (live smoke / fixture e2e / known gaps)
- [`docs/graphql-versioning.md`](docs/graphql-versioning.md) — schema
  versioning policy

## Development

The project uses an `uv` workspace covering `apps/api/` plus the shared
`packages/unifi-core/` and three MCP apps. Common development commands:

```bash
# Install everything once
uv sync --all-packages

# Run the unifi-api-server test suite (~700 tests)
uv run --package unifi-api-server pytest apps/api/tests

# Run live smoke against real controllers (requires .env)
uv run --package unifi-api-server python scripts/live_api_smoke.py --output /tmp/smoke.json

# Re-export drift-gated artifacts after schema changes
uv run --package unifi-api-server python -m unifi_api.graphql.docgen
```

The full project quality gate runs `make pre-commit` (lint + format + sync-skills
+ tests) at the repo root.

## License

See the repository root [LICENSE](../../LICENSE) file. MIT License, © 2025 Chris Kirby.
