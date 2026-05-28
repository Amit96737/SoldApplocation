from typing import List, Optional

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session
from starlette import status
from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.websockets import WebSocketDisconnect, WebSocket

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from exception import UnicornException
from . import crud, schemas
from .manager import chat_socket_manager

router = APIRouter(
    prefix="/chat",
)


@router.post("/{room_id}/messages", tags=["Chat"], response_model=schemas.MessageInDb)
async def send_message(room_id: str, background_tasks: BackgroundTasks, message_data: schemas.SendMessage,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    result = await crud.send_message(room_id, background_tasks, message_data, current_user, db)
    return result


@router.post("/send-offer", tags=["Chat"])
async def send_offer(request: Request, background_tasks: BackgroundTasks, offer_data: schemas.SendOffer,
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await crud.send_offer(request, offer_data, background_tasks, current_user, db)
    return result


@router.websocket("/messages/{room_id}/{user_id}")
async def listen_to_messages(room_id: str, user_id: str, websocket: WebSocket):
    await websocket.accept()
    await chat_socket_manager.connect(websocket, room_id, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            print(data)
            print(f"Received: {data}")
    except WebSocketDisconnect:
        chat_socket_manager.disconnect(websocket)


@router.get("/{room_id}/messages", tags=["Chat"])
async def get_room_messages(room_id: str, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return crud.get_room_messages(room_id, db, current_user)


@router.get("/room", tags=["Chat"])
async def get_chat_room(room_data: schemas.GetRoomSchema, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):

    chatRoom = crud.get_chat_room(room_data, current_user, db, "en")
    if not chatRoom:
        raise UnicornException(
            status_code=status.HTTP_404_NOT_FOUND, message="Chat room not found")

    return chatRoom


@router.post("/message/{message_id}", tags=["Chat"])
async def mark_as_read(message_id: str, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return crud.mark_as_read(message_id, db, current_user)


@router.get("/rooms", tags=["Chat"])
async def get_user_chatroom(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.get_user_chat_rooms(current_user, db, request=request)


@router.delete("/rooms", tags=["Chat"])
async def delete_chat_room(room_list: List[str], db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return crud.delete_room(room_list, db)


@router.get("/user/{user_id}", tags=["Chat"])
async def get_chat_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.get_chat_user(user_id, db)




