from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.actions.action_manager import (
    get_action, list_pending, approve_and_execute, deny_action
)

router = APIRouter()

class ApproveBody(BaseModel):
    approve: bool

@router.get("/pending")
def pending_actions():
    return list_pending()

@router.post("/{action_id}")
def approve_or_deny(action_id: str, body: ApproveBody):
    action = get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if body.approve:
        updated = approve_and_execute(action_id)
    else:
        updated = deny_action(action_id)

    return updated
