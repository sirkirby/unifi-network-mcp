# GraphQL Schema Versioning Policy

The unifi-api GraphQL schema follows additive evolution — non-breaking
changes can land freely; breaking changes require an explicit deprecation
cycle.

## Non-breaking changes (always allowed)

- Adding a new field to an existing type
- Adding a new type
- Adding a new enum value
- Adding an optional argument with a default value
- Broadening nullability (required → optional)

## Breaking changes (require deprecation cycle)

- Removing a field
- Removing a type
- Removing an enum value
- Narrowing a type (e.g., `String` → `Int`)
- Narrowing nullability (optional → required without a default)
- Renaming a field, type, or enum value (= remove + add)

## Deprecation cycle

1. Mark with `@strawberry.deprecated(reason="use X instead")` on the Python
   field/type definition.
2. Field stays with the deprecation marker for at least one minor release.
3. Removal in a later release.

## Enforcement

The CI gate `test_versioning_policy` compares the live schema against the
checked-in `schema.graphql` artifact. Any field that exists in the artifact
but not the live schema (i.e., was removed) must have had a `deprecation_reason`
set in the artifact — otherwise the gate fails. Hard fail on un-deprecated
removals.
