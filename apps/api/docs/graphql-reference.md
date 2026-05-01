# unifi-api GraphQL Reference

> Auto-generated from the Strawberry schema by `unifi_api.graphql.docgen`.
> Do not edit by hand. Regenerate with `python -m unifi_api.graphql.docgen`.

## Schema (SDL)

```graphql
"""Service health snapshot — smoke field for the GraphQL endpoint."""
type HealthSnapshot {
  ok: Boolean!
  version: String!
  pythonVersion: String!
}

type Query {
  """Liveness probe; mirrors GET /v1/health/ready."""
  health: HealthSnapshot!
}
```
