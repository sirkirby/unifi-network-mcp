"""Action endpoint: POST /v1/actions/{tool_name}."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from unifi_api.auth.middleware import require_scope
from unifi_api.auth.scopes import Scope
from unifi_api.services import actions as actions_svc
from unifi_api.services.audit import write_audit
from unifi_api.services.controllers import ControllerNotFound, get_controller
from unifi_api.services.manifest import ToolNotFound


router = APIRouter()


class ActionIn(BaseModel):
    site: str
    controller: str
    args: dict = {}
    confirm: bool = False


def _to_jsonable(x):
    """Best-effort coerce a manager return value to a JSON-serializable form.

    The Phase 2 dispatcher (Option D AST introspection) routes from tool_name to
    the underlying manager method, bypassing the MCP tool function's
    response-shaping layer. Manager methods like ClientManager.get_clients()
    return list[aiounifi.models.client.Client] (Pydantic-ish objects), not
    dicts. This helper coerces them.

    Phase 3 will add proper resource serializers; this is the v1 floor.
    """
    if hasattr(x, "raw"):  # aiounifi models expose .raw with the dict payload
        return x.raw
    if hasattr(x, "model_dump"):
        return x.model_dump()
    if hasattr(x, "dict") and callable(x.dict):
        try:
            return x.dict()
        except Exception:
            pass
    return x


def _coerce_response(result) -> dict:
    """Normalize manager output to a {success, data} dict."""
    if isinstance(result, dict):
        return result
    if isinstance(result, (list, tuple)):
        return {"success": True, "data": [_to_jsonable(item) for item in result]}
    if isinstance(result, (str, int, float, bool)) or result is None:
        return {"success": True, "data": result}
    return {"success": True, "data": _to_jsonable(result)}


@router.post(
    "/actions/{tool_name}",
    dependencies=[Depends(require_scope(Scope.WRITE))],
)
async def post_action(request: Request, tool_name: str, body: ActionIn) -> dict:
    sm = request.app.state.sessionmaker
    factory = request.app.state.manager_factory
    registry = request.app.state.manifest_registry
    key_prefix = getattr(request.state, "api_key_prefix", "(unknown)")

    async with sm() as session:
        try:
            controller = await get_controller(session, body.controller)
        except ControllerNotFound:
            await write_audit(
                session,
                key_id_prefix=key_prefix,
                controller=None,
                target=tool_name,
                outcome="error",
                error_kind="controller_not_found",
            )
            await session.commit()
            raise HTTPException(status_code=404, detail="controller not found")

        controller_products = [p for p in controller.product_kinds.split(",") if p]
        try:
            result = await actions_svc.dispatch_action(
                registry=registry,
                factory=factory,
                session=session,
                tool_name=tool_name,
                controller_id=body.controller,
                controller_products=controller_products,
                site=body.site,
                args=body.args,
                confirm=body.confirm,
            )
            coerced = _coerce_response(result)
            outcome = "success" if coerced.get("success", True) else "error"
            await write_audit(
                session,
                key_id_prefix=key_prefix,
                controller=body.controller,
                target=tool_name,
                outcome=outcome,
            )
            await session.commit()
            return coerced
        except ToolNotFound:
            await write_audit(
                session,
                key_id_prefix=key_prefix,
                controller=body.controller,
                target=tool_name,
                outcome="error",
                error_kind="unknown_tool",
            )
            await session.commit()
            return {"success": False, "error": f"unknown tool: {tool_name}"}
        except actions_svc.CapabilityMismatch as e:
            await write_audit(
                session,
                key_id_prefix=key_prefix,
                controller=body.controller,
                target=tool_name,
                outcome="error",
                error_kind="capability_mismatch",
            )
            await session.commit()
            return {"success": False, "error": str(e)}
        except Exception as e:
            await write_audit(
                session,
                key_id_prefix=key_prefix,
                controller=body.controller,
                target=tool_name,
                outcome="error",
                error_kind=type(e).__name__,
                detail=str(e),
            )
            await session.commit()
            return {"success": False, "error": f"{type(e).__name__}: {e}"}
