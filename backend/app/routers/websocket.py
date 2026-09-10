import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["Real-Time Synchronization"])
logger = logging.getLogger("oasis.websocket_router")


@router.websocket("/ws/vendor/{restaurant_id}")
async def vendor_websocket_endpoint(websocket: WebSocket, restaurant_id: int):
    """
    WebSocket channel for the B2B Vendor Dashboard.
    Receives instant real-time broadcasts when:
    - RESERVATION_CREATED (Customer or API bookings)
    - RESERVATION_STATUS_UPDATED (Confirmed, Seated, Cancelled, Completed)
    - TABLE_STATUS_CHANGED (Manual table blocks, Walk-in guests seated)
    """
    await ws_manager.connect(restaurant_id, websocket)
    try:
        # Initial welcome message
        await websocket.send_json({
            "event": "CONNECTED",
            "restaurant_id": restaurant_id,
            "message": f"Real-time stream connected for restaurant {restaurant_id}"
        })

        while True:
            # Keep connection open; receive heartbeats or ping frames
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(restaurant_id, websocket)
    except Exception as exc:
        logger.warning(f"[WS] Unexpected WebSocket error on restaurant {restaurant_id}: {exc}")
        ws_manager.disconnect(restaurant_id, websocket)
