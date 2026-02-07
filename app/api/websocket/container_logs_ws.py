import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/logs/{container_name}")
async def log_stream(websocket: WebSocket, container_name: str):
    await websocket.accept()
    print(f"🔌 WebSocket connected: {container_name}")

    try:
        # Register this websocket as a log listener
        from app.services.docker.log_broadcaster import register_client
        register_client(container_name, websocket)

        while True:
            # Keep connection alive (client doesn't need to send anything)
            await websocket.receive_text()

    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected: {container_name}")
        from app.services.docker.log_broadcaster import unregister_client
        unregister_client(container_name, websocket)
