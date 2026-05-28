from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from starlette.requests import Request
from notification.manager import notification_manager
from . import crud

router = APIRouter(
    prefix="/notifications",
)


@router.websocket("/listen")
async def notifications_socket(user_id: str, websocket: WebSocket):
    await notification_manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            print(data)
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket)


@router.get("", tags=["Notification"])
async def get_user_notifications(request: Request, current_user: User = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    return crud.get_user_notification(request, current_user, db)


@router.post("/{notification_id}/mark-as-read", tags=["Notification"])
async def mark_as_read(notification_id: str, db: Session = Depends(get_db)):
    return crud.mark_as_read(notification_id, db)


@router.delete("/{notification_id}", tags=["Notification"])
async def delete_notification(notification_id: str, db: Session = Depends(get_db)):
    return crud.delete_notification(notification_id, db)