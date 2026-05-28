from fastapi import WebSocket


async def send_personal_message(message: dict, websocket: WebSocket):
    await websocket.send_json(message)


class NotificationWebSocketManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.append({"websocket": websocket, "user_id": user_id})

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [
            conn for conn in self.active_connections if conn["websocket"] != websocket
        ]

    async def send_personal_message(self, message: dict, user_id: str):
        for connection in self.active_connections:
            if connection["user_id"] == user_id:
                await connection["websocket"].send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


def create_notification_manager():
    return NotificationWebSocketManager()


notification_manager = create_notification_manager()
