from typing import Dict, List, Any
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.
    """
    def __init__(self):
        # user_id -> [WebSockets]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: Any, user_id: int):
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except:
                    # Clean up broken connections
                    pass

    async def broadcast(self, message: Any):
        for connections in self.active_connections.values():
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                except:
                    pass

manager = ConnectionManager()
