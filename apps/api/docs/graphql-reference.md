# unifi-api GraphQL Reference

> Auto-generated from the Strawberry schema by `unifi_api.graphql.docgen`.
> Do not edit by hand. Regenerate with `python -m unifi_api.graphql.docgen`.

## Schema (SDL)

```graphql
"""A client device on the UniFi Network controller."""
type Client {
  mac: ID
  ip: String
  hostname: String
  isWired: Boolean!
  isGuest: Boolean!
  status: String!
  lastSeen: String
  firstSeen: String
  note: String
  usergroupId: String
}

"""Paginated page of clients."""
type ClientPage {
  items: [Client!]!
  nextCursor: String
}

"""A UniFi network device (AP, switch, gateway)."""
type Device {
  mac: ID
  name: String
  model: String
  type: String
  version: String
  uptime: Int
  state: String
  ip: String
  ports: JSON
}

"""Paginated page of devices."""
type DevicePage {
  items: [Device!]!
  nextCursor: String
}

"""Service health snapshot — smoke field for the GraphQL endpoint."""
type HealthSnapshot {
  ok: Boolean!
  version: String!
  pythonVersion: String!
}

"""
The `JSON` scalar type represents JSON values as specified by [ECMA-404](https://ecma-international.org/wp-content/uploads/ECMA-404_2nd_edition_december_2017.pdf).
"""
scalar JSON @specifiedBy(url: "https://ecma-international.org/wp-content/uploads/ECMA-404_2nd_edition_december_2017.pdf")

"""A UniFi LAN/VLAN network configuration."""
type Network {
  id: ID
  name: String
  purpose: String
  enabled: Boolean!
  vlan: Int
  subnet: String
}

"""Paginated page of network configurations."""
type NetworkPage {
  items: [Network!]!
  nextCursor: String
}

"""Read-only access to UniFi Network resources."""
type NetworkQuery {
  """List clients on the given controller/site (paginated)."""
  clients(controller: ID!, site: String! = "default", limit: Int! = 50, cursor: String = null): ClientPage!

  """List devices on the given controller/site (paginated)."""
  devices(controller: ID!, site: String! = "default", limit: Int! = 50, cursor: String = null): DevicePage!

  """
  List configured LAN/VLAN networks on the given controller/site (paginated).
  """
  networks(controller: ID!, site: String! = "default", limit: Int! = 50, cursor: String = null): NetworkPage!
}

type Query {
  """Liveness probe; mirrors GET /v1/health/ready."""
  health: HealthSnapshot!

  """Read-only access to UniFi Network resources."""
  network: NetworkQuery!
}
```
