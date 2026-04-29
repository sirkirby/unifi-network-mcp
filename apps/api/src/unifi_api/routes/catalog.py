"""Catalog endpoints — discoverability for tools, categories, render hints."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Request

from unifi_api.auth.middleware import require_scope
from unifi_api.auth.scopes import Scope


router = APIRouter()


@router.get("/catalog/tools", dependencies=[Depends(require_scope(Scope.READ))])
async def get_tools(request: Request) -> dict:
    manifest = request.app.state.manifest_registry
    serializer_registry = request.app.state.serializer_registry
    items = []
    for tool_name in manifest.all_tools():
        entry = manifest.resolve(tool_name)
        try:
            render_hint = serializer_registry.render_hint_for_tool(tool_name)
        except Exception:
            render_hint = {"kind": "empty"}
        items.append({
            "name": tool_name,
            "product": entry.product,
            "category": entry.category,
            "manager": entry.manager,
            "method": entry.method,
            "render_hint": render_hint,
        })
    return {"items": items}


@router.get("/catalog/categories", dependencies=[Depends(require_scope(Scope.READ))])
async def get_categories(request: Request) -> dict:
    manifest = request.app.state.manifest_registry
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for tool_name in manifest.all_tools():
        entry = manifest.resolve(tool_name)
        counts[(entry.product, entry.category or "")] += 1
    items = [
        {"product": p, "category": c, "tool_count": n}
        for (p, c), n in sorted(counts.items())
    ]
    return {"items": items}


@router.get("/catalog/render-hints", dependencies=[Depends(require_scope(Scope.READ))])
async def get_render_hints(request: Request) -> dict:
    manifest = request.app.state.manifest_registry
    serializer_registry = request.app.state.serializer_registry
    by_kind: dict[str, dict] = {}
    for tool_name in manifest.all_tools():
        try:
            kind = serializer_registry.kind_for_tool(tool_name).value
        except Exception:
            continue
        by_kind.setdefault(kind, {"kind": kind, "tools": [], "resources": []})
        by_kind[kind]["tools"].append(tool_name)
    for product, resource in serializer_registry.all_resources():
        try:
            kind = serializer_registry.kind_for_resource(product, resource).value
        except Exception:
            continue
        by_kind.setdefault(kind, {"kind": kind, "tools": [], "resources": []})
        by_kind[kind]["resources"].append({"product": product, "path": resource})
    return {"items": list(by_kind.values())}
