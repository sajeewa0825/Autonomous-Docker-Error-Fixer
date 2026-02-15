from collections import defaultdict
from fastapi import WebSocket
from typing import Any, Dict
import json

listeners = defaultdict(set)

def register_client(container_name: str, websocket: WebSocket):
    listeners[container_name].add(websocket)

def unregister_client(container_name: str, websocket: WebSocket):
    listeners[container_name].discard(websocket)

async def broadcast_event(container_name: str, payload: Dict[str, Any]):
    """
    Send structured events to UI.
    payload example:
      {"type":"log","line":"..."}
      {"type":"analysis","status":"error","summary":"..."}
      {"type":"approval_required","action_id":"...","command":"...","confidence":0.82}
      {"type":"action_result","action_id":"...","status":"executed","message":"..."}
    """
    msg = json.dumps(payload, ensure_ascii=False)
    for ws in list(listeners[container_name]):
        try:
            await ws.send_text(msg)
        except Exception:
            listeners[container_name].discard(ws)

# Backward-compatible helper if you still want "line only"
async def broadcast_log(container_name: str, line: str):
    await broadcast_event(container_name, {"type": "log", "line": line})
