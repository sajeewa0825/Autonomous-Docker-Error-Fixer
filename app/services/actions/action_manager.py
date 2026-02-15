from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from uuid import uuid4
from datetime import datetime

import docker
import subprocess
import shlex

from app.core.loadenv import Settings

docker_client = docker.from_env()

@dataclass
class PendingAction:
    action_id: str
    container_name: str
    command: str
    confidence: float
    source: str              # "rag" | "web" | "recommendation" | "unknown"
    reason: str
    created_at: str
    status: str              # "pending" | "approved" | "denied" | "executed" | "failed"
    result_message: str = ""

PENDING: Dict[str, PendingAction] = {}

def create_action(container_name: str, command: str, confidence: float, source: str, reason: str) -> PendingAction:
    action_id = str(uuid4())
    action = PendingAction(
        action_id=action_id,
        container_name=container_name,
        command=command,
        confidence=float(confidence),
        source=source,
        reason=reason,
        created_at=datetime.utcnow().isoformat() + "Z",
        status="pending",
    )
    PENDING[action_id] = action
    return action

def get_action(action_id: str) -> Optional[PendingAction]:
    return PENDING.get(action_id)

def list_pending():
    return [asdict(x) for x in PENDING.values() if x.status == "pending"]

def deny_action(action_id: str) -> Optional[PendingAction]:
    action = PENDING.get(action_id)
    if not action:
        return None
    action.status = "denied"
    action.result_message = "Denied by human."
    return action

def _exec_allowed(command: str, container_name: str) -> str:
    """
    SAFE executor: allow-list only. No eval().
    Returns message.
    """
    cmd = command.strip()

    # --- Docker SDK patterns (we map to safe calls) ---
    # client.containers.get("<name>").restart()
    if cmd.startswith("client.containers.get(") and cmd.endswith(").restart()"):
        docker_client.containers.get(container_name).restart()
        return "Container restarted."

    # client.containers.get("<name>").kill(signal="SIGKILL")
    if cmd.startswith("client.containers.get(") and ".kill" in cmd:
        docker_client.containers.get(container_name).kill(signal="SIGKILL")
        return "Container killed with SIGKILL."

    # --- Shell commands allow-list (VERY limited) ---
    allowed_prefixes = [
        "docker system prune -f",
        "docker system prune -f --volumes",
        "docker image prune -f",
        "docker network prune -f",
    ]
    for pref in allowed_prefixes:
        if cmd.startswith(pref):
            subprocess.run(shlex.split(cmd), check=False, capture_output=True, text=True)
            return f"Executed shell command: {pref}"

    # You can add more safe actions here if needed.
    raise ValueError("Command blocked by allow-list.")

def approve_and_execute(action_id: str) -> Optional[PendingAction]:
    action = PENDING.get(action_id)
    if not action:
        return None

    action.status = "approved"
    try:
        msg = _exec_allowed(action.command, action.container_name)
        action.status = "executed"
        action.result_message = msg
    except Exception as e:
        action.status = "failed"
        action.result_message = str(e)

    return action

def needs_human_approval(confidence: float) -> bool:
    return float(confidence) < float(Settings.APPROVAL_MIN_CONFIDENCE)

def should_auto_execute(confidence: float) -> bool:
    return bool(Settings.AUTO_EXECUTE_FIXES) and not needs_human_approval(confidence)
