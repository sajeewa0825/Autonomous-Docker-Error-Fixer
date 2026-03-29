from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.actions.action_manager import (
    get_action,
    list_pending,
    approve_and_execute,
    deny_action,
)
from app.services.docker.log_broadcaster import broadcast_event

router = APIRouter()


class ActionDecisionRequest(BaseModel):
    approve: bool


@router.get("/")
def get_pending_actions():
    return {"items": list_pending()}


@router.get("/{action_id}")
def get_one_action(action_id: str):
    action = get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return asdict(action)


@router.post("/{action_id}")
async def decide_action(action_id: str, payload: ActionDecisionRequest):
    action = get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if payload.approve:
        updated = approve_and_execute(action_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Action not found")

        # ✅ CRITICAL FIX: broadcast result so UI clears "Executing..."
        await broadcast_event(updated.container_name, {
            "type": "action_result",
            "action_id": updated.action_id,
            "status": updated.status,
            "message": updated.result_message,
            "command": updated.command,
            "confidence": updated.confidence,
            "source": updated.source,
            "reason": updated.reason,
        })

        return {
            "ok": True,
            "action": asdict(updated)
        }

    updated = deny_action(action_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Action not found")

    # ✅ Broadcast denied result too, so UI also clears correctly
    await broadcast_event(updated.container_name, {
        "type": "action_result",
        "action_id": updated.action_id,
        "status": updated.status,
        "message": updated.result_message,
        "command": updated.command,
        "confidence": updated.confidence,
        "source": updated.source,
        "reason": updated.reason,
    })

    return {
        "ok": True,
        "action": asdict(updated)
    }