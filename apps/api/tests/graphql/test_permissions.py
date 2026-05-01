"""Strawberry permission classes for read/admin scope checks on GraphQL fields."""

from unifi_api.graphql.context import GraphQLContext
from unifi_api.graphql.permissions import IsAdmin, IsRead


def _info_with_scopes(scopes: str):
    """Build a fake Info.context with the given scopes string."""

    class _FakeInfo:
        context = GraphQLContext(api_key_scopes=scopes)

    return _FakeInfo()


def test_is_read_matches_rest_scope_semantics() -> None:
    """IsRead matches REST scope_allows(held, Scope.READ): admin or explicit read.
    Write-only keys do NOT pass — there is no write→read implication, same as REST.
    """
    assert IsRead().has_permission(None, _info_with_scopes("read")) is True
    assert IsRead().has_permission(None, _info_with_scopes("admin")) is True
    assert IsRead().has_permission(None, _info_with_scopes("read,write")) is True
    assert IsRead().has_permission(None, _info_with_scopes("write")) is False
    assert IsRead().has_permission(None, _info_with_scopes("")) is False


def test_is_admin_only_admin() -> None:
    assert IsAdmin().has_permission(None, _info_with_scopes("admin")) is True
    assert IsAdmin().has_permission(None, _info_with_scopes("write")) is False
    assert IsAdmin().has_permission(None, _info_with_scopes("read")) is False
    assert IsAdmin().has_permission(None, _info_with_scopes("read,write")) is False
