import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("oasis.websocket")


class ConnectionManager:
    """
    Manages active WebSocket connections partitioned by restaurant_id.
    Broadcasts real-time events to connected vendor dashboard clients.
    """
    def __init__(self):
        # Maps restaurant_id -> set of active WebSockets
        self._rooms: Dict[int, Set[WebSocket]] = {}

    async def connect(self, restaurant_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        if restaurant_id not in self._rooms:
            self._rooms[restaurant_id] = set()
        self._rooms[restaurant_id].add(websocket)
        logger.info(
            f"[WS] Client connected to restaurant {restaurant_id}. "
            f"Active connections in room: {len(self._rooms[restaurant_id])}"
        )

    def disconnect(self, restaurant_id: int, websocket: WebSocket) -> None:
        if restaurant_id in self._rooms:
            self._rooms[restaurant_id].discard(websocket)
            if not self._rooms[restaurant_id]:
                del self._rooms[restaurant_id]
        logger.info(f"[WS] Client disconnected from restaurant {restaurant_id}.")

    async def broadcast(self, restaurant_id: int, event_type: str, data: Any) -> None:
        """
        Broadcasts an event with a standardized payload to all active vendor connections.
        """
        if restaurant_id not in self._rooms:
            logger.debug(f"[WS] No active vendor connections listening for restaurant {restaurant_id}")
            return

        message = {
            "event": event_type,
            "restaurant_id": restaurant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        serialized = json.dumps(message, default=str)
        
        dead_connections = set()
        for connection in self._rooms[restaurant_id]:
            try:
                await connection.send_text(serialized)
            except Exception as exc:
                logger.warning(f"[WS] Error dispatching message to a connection: {exc}")
                dead_connections.add(connection)

        # Cleanup any broken connections
        for dead in dead_connections:
            self.disconnect(restaurant_id, dead)


ws_manager = ConnectionManager()
