"""Re-exported / wrapper Pydantic models for REST routes.

The Page wrapper matches the canonical pagination envelope returned by
list endpoints: {items, next_cursor, render_hint}. REST routes use
``response_model=Page[to_pydantic_model(SomeType)]``.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="allow")
    items: list[T]
    next_cursor: str | None = None
    render_hint: dict | None = None
