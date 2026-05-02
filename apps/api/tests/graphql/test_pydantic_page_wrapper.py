"""Page wrapper accepts a typed item list and the canonical envelope."""

from __future__ import annotations

from unifi_api.graphql.pydantic_export import to_pydantic_model
from unifi_api.graphql.types.network.client import Client
from unifi_api.services.pydantic_models import Detail, Page


def test_page_accepts_typed_items() -> None:
    ItemModel = to_pydantic_model(Client)
    PageOfClients = Page[ItemModel]
    page = PageOfClients(
        items=[{"mac": "aa:01", "hostname": "x", "is_wired": True}],
        next_cursor=None,
        render_hint=None,
    )
    assert page.items[0].mac == "aa:01"


def test_page_accepts_extras_in_envelope() -> None:
    ItemModel = to_pydantic_model(Client)
    PageOfClients = Page[ItemModel]
    PageOfClients(items=[], next_cursor="abc", render_hint={"k": "v"})


def test_detail_accepts_typed_data() -> None:
    ItemModel = to_pydantic_model(Client)
    DetailOfClient = Detail[ItemModel]
    detail = DetailOfClient(
        data={"mac": "aa:01", "hostname": "x", "is_wired": True},
        render_hint=None,
    )
    assert detail.data.mac == "aa:01"


def test_detail_accepts_extras_in_envelope() -> None:
    ItemModel = to_pydantic_model(Client)
    DetailOfClient = Detail[ItemModel]
    DetailOfClient(data={"mac": "aa:01"}, render_hint={"k": "v"})
