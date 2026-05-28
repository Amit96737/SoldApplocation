from fastapi import WebSocket
from chats import schemas


async def send_personal_message(message: dict, websocket: WebSocket):
    await websocket.send_json(message)


class ChatWebSocketManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        self.active_connections.append({"websocket": websocket, "room_id": room_id, "user_id": user_id})

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [
            conn for conn in self.active_connections if conn["websocket"] != websocket
        ]


def create_chat_manager():
    return ChatWebSocketManager()


chat_socket_manager = create_chat_manager()
