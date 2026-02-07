from collections import defaultdict
from fastapi import WebSocket

listeners = defaultdict(set)

def register_client(container_name: str, websocket: WebSocket):
    listeners[container_name].add(websocket)

def unregister_client(container_name: str, websocket: WebSocket):
    listeners[container_name].discard(websocket)

async def broadcast_log(container_name: str, line: str):
    for ws in list(listeners[container_name]):
        try:
            await ws.send_text(line)
        except Exception:
            listeners[container_name].discard(ws)
