"""Scope definitions and check helpers."""

from __future__ import annotations

import enum


class Scope(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


def parse_scopes(s: str) -> frozenset[Scope]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    out: set[Scope] = set()
    for p in parts:
        try:
            out.add(Scope(p))
        except ValueError as e:
            raise ValueError(f"unknown scope: {p}") from e
    return frozenset(out)


def scope_allows(held: frozenset[Scope], required: Scope) -> bool:
    if Scope.ADMIN in held:
        return True
    return required in held
