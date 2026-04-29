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
            outcome = (
                "success"
                if isinstance(result, dict) and result.get("success", True)
                else "error"
            )
            await write_audit(
                session,
                key_id_prefix=key_prefix,
                controller=body.controller,
                target=tool_name,
                outcome=outcome,
            )
            await session.commit()
            return result
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
