import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/logs/{container_name}")
async def log_stream(websocket: WebSocket, container_name: str):
    await websocket.accept()
    print(f"🔌 WebSocket connected: {container_name}")

    from app.services.docker.log_broadcaster import register_client, unregister_client
    register_client(container_name, websocket)

    try:
        # Keep alive, no need client messages
        while True:
            await asyncio.sleep(30)
            # optional ping payload
            await websocket.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected: {container_name}")
    except Exception:
        pass
    finally:
        unregister_client(container_name, websocket)
