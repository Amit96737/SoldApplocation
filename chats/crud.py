import json
from datetime import datetime
from typing import List
from uuid import uuid4

from fastapi import status, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_
from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks
from starlette.requests import Request

import helper
from I18n.load_language import get_lang_content
from auth.crud import get_user_by_id
from auth.models import User
from exception import UnicornException
from helper import calculate_average
from notification.manager import notification_manager
from profile import crud as profile_crud
from ratings.models import UserRatings
from shop.schemas import ShopItem
from . import models, schemas
from .manager import chat_socket_manager
from notification import crud as notification_crud
from notification.schemas import NotificationType, NotificationBase
from shop import models as shop_models
from auth.schemas import AccountStatus
from shop.crud import translate_text

def create_chat_room(current_user: User, room_data: schemas.SendMessage, db: Session):
    unique_id = str(uuid4())

    usersInRoom = []
    usersInRoom.extend([current_user.id, room_data.receiver_id])

    chatroom_model = models.ChatRoom(
        id=unique_id,
        users=json.dumps(usersInRoom),
        item_id=room_data.item_id,
        last_message=room_data.message,
        last_message_by=current_user.id,
        last_message_type=room_data.message_type,
        last_item_price=room_data.item_price,
        last_offer_price=room_data.offer_price,
    )

    db.add(chatroom_model)
    db.commit()
    db.refresh(chatroom_model)

    return chatroom_model


async def send_message(room_id: str, backgroundTasks: BackgroundTasks, message_data: schemas.SendMessage,
                       current_user: User, db: Session):
    receiver = get_user_by_id(message_data.receiver_id, db)

    if current_user.id == message_data.receiver_id:
        raise UnicornException(
            status_code=status.HTTP_403_FORBIDDEN, message="You can't message yourself")

    if not receiver or receiver.account_status == AccountStatus.Deleted:
        raise UnicornException(
            status_code=status.HTTP_404_NOT_FOUND, message="User with this id not found")

    unique_id = str(uuid4())
    chatRoomInDb = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id).first()

    def notify_receiver():
        chat_socket_users = [conn['user_id'] for conn in chat_socket_manager.active_connections]

        if message_data.receiver_id in chat_socket_users:
            message_model.is_read = True
            db.commit()

            backgroundTasks.add_task(notification_crud.notify_websocket, jsonable_encoder(message_schema),
                                     chat_socket_manager, message_data.receiver_id, chatRoomInDb.id)

        else:
            notification_socket_users = [conn['user_id'] for conn in notification_manager.active_connections]

            if message_data.receiver_id in notification_socket_users:
                backgroundTasks.add_task(notification_crud.notify_websocket, {"type": "new-message"},
                                         notification_manager, message_data.receiver_id)

            else:
                notificationCreateSchema = NotificationBase(
                    receiver_id=message_data.receiver_id,
                    type=NotificationType.NewMessage
                )

                sender_profile = profile_crud.get_user_profile_schema(current_user, db)

                notificationData = notification_crud.get_notification_data(notificationCreateSchema.type,
                                                                           {"sender_name": sender_profile.fullname,
                                                                            "sender_pic": sender_profile.profile_pic,
                                                                            "message_content": message_data.message
                                                                            })

                backgroundTasks.add_task(notification_crud.send_push_notification, notificationCreateSchema,
                                         notificationData.get('headings'), notificationData.get('contents'), db,
                                         notificationData.get('subtitle'), notificationData.get('small_icon'))

    if chatRoomInDb:
        message_model = models.Message(
            id=unique_id,
            room_id=room_id,
            sender_id=current_user.id,
            offer_price=message_data.offer_price,
            message_type=message_data.message_type,
            message=message_data.message,
            attachments=json.dumps(message_data.attachments)
        )

        db.add(message_model)
        chatRoomInDb.last_message_at = datetime.utcnow()
        chatRoomInDb.last_message_by = current_user.id
        chatRoomInDb.last_message = message_data.message
        chatRoomInDb.last_message_type = message_data.message_type
        chatRoomInDb.last_offer_price = message_data.offer_price
        chatRoomInDb.last_item_price = message_data.item_price
        db.commit()
        db.refresh(message_model)

        message_schema = schemas.MessageInDb.model_validate(message_model)

        notify_receiver()

        return message_schema

    else:
        chatModel = create_chat_room(current_user, message_data, db)
        message_model = models.Message(
            id=unique_id,
            message=message_data.message,
            room_id=chatModel.id,
            sender_id=current_user.id,
            offer_price=message_data.offer_price,
            message_type=message_data.message_type,
            attachments=json.dumps(message_data.attachments)
        )

        db.add(message_model)
        db.commit()
        db.refresh(message_model)

        message_schema = schemas.MessageInDb.model_validate(message_model)

        notify_receiver()

        return message_schema


async def send_offer(request: Request, offer_data: schemas.SendOffer, backgroundTasks: BackgroundTasks,
                     current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)
    itemInDb = db.query(shop_models.ShopItem).filter_by(id=offer_data.item_id).first()

    if not itemInDb:
        raise UnicornException(
            status_code=status.HTTP_404_NOT_FOUND, message="Item with this id not found")

    if current_user.id == itemInDb.owner_id:
        raise UnicornException(
            status_code=status.HTTP_403_FORBIDDEN, message="You can't send an offer to yourself")

    if not itemInDb.owner or itemInDb.owner.account_status in [AccountStatus.Deleted, AccountStatus.Disabled]:
        raise UnicornException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=language_content.get("an error occurred while sending an offer"))

    chatRoom = get_chat_room(
        schemas.GetRoomSchema(
            user_id=itemInDb.owner_id,
            item_id=offer_data.item_id
        ), current_user, db, language_content
    )

    def notify_receiver():
        chat_socket_users = [conn['user_id'] for conn in chat_socket_manager.active_connections]

        if itemInDb.owner_id in chat_socket_users:
            message_model.is_read = True
            db.commit()

            backgroundTasks.add_task(notification_crud.notify_websocket, jsonable_encoder(message_schema),
                                     chat_socket_manager, itemInDb.owner_id, chatRoom.id)

        else:
            notification_socket_users = [conn['user_id'] for conn in notification_manager.active_connections]

            if itemInDb.owner_id in notification_socket_users:
                backgroundTasks.add_task(notification_crud.notify_websocket, {"type": "new-message"},
                                         notification_manager,
                                         itemInDb.owner_id)

            else:
                notificationCreateSchema = NotificationBase(
                    receiver_id=itemInDb.owner_id,
                    type=NotificationType.NewOffer
                )

                sender_profile = profile_crud.get_user_profile_schema(current_user, db)

                notificationData = notification_crud.get_notification_data(notificationCreateSchema.type,
                                                                           {"sender_name": sender_profile.fullname,
                                                                            "sender_pic": sender_profile.profile_pic,
                                                                            "message_content": "Made an offer"
                                                                            })

                backgroundTasks.add_task(notification_crud.send_push_notification, notificationCreateSchema,
                                         notificationData.get('headings'), notificationData.get('contents'), db,
                                         notificationData.get('subtitle'), notificationData.get('small_icon'))

    if chatRoom:
        unique_id = str(uuid4())
        message_model = models.Message(
            id=unique_id,
            room_id=chatRoom.id,
            item_price=itemInDb.price,
            sender_id=current_user.id,
            offer_price=offer_data.offer_price,
            message_type=schemas.MessageType.Offer,
        )

        chatRoomInDb = db.query(models.ChatRoom).filter(models.ChatRoom.id == chatRoom.id).first()

        db.add(message_model)
        chatRoomInDb.last_message_at = datetime.utcnow()
        chatRoomInDb.last_message_by = current_user.id
        chatRoomInDb.last_message_type = message_model.message_type
        chatRoomInDb.last_offer_price = message_model.offer_price
        chatRoomInDb.last_item_price = message_model.item_price
        db.commit()
        db.refresh(message_model)

        message_schema = schemas.MessageInDb.model_validate(message_model)

        notify_receiver()

        return message_schema

    else:
        unique_id = str(uuid4())

        chatModel = create_chat_room(current_user, schemas.SendMessage(
            **offer_data.__dict__,
            item_price=itemInDb.price,
            receiver_id=itemInDb.owner_id,

            message_type=schemas.MessageType.Offer
        ), db)

        message_model = models.Message(
            id=unique_id,
            room_id=chatModel.id,
            sender_id=current_user.id,
            offer_price=offer_data.offer_price,
            message_type=schemas.MessageType.Offer
        )

        db.add(message_model)
        db.commit()
        db.refresh(message_model)

        message_schema = schemas.MessageInDb.model_validate(message_model)

        notify_receiver()

        return message_schema


def get_user_chat_rooms(current_user: User, db: Session, request: Request):
    # lang = request.headers.get('X-language', 'en')
    # language_content = get_lang_content(lang)
    language_code = "en"

    chatRoomsInDb = db.query(models.ChatRoom).filter(models.ChatRoom.users.contains(current_user.id)).all()
    # all_chatRooms=[]
    message_chats = []
    offer_chats = []

    for room in chatRoomsInDb:
        roomUsers = json.loads(room.users)
        roomUsers.remove(current_user.id)
        otherUserId = ''.join(roomUsers)

        chatUserSchema = get_chat_user(otherUserId, db)

        unReadMessages = [message for message in room.messages if
                          not message.is_read and message.sender_id != current_user.id]

        # chatRoomSchema = schemas.ChatRoomInDb.model_validate(room)
        chatRoomSchema = schemas.ChatRoomInDb.model_validate(room,from_attributes=True)

        chatRoomSchema.item = ShopItem.model_validate(room.item) if room.item else None
        chatRoomSchema.user = chatUserSchema
        chatRoomSchema.unread_count = len(unReadMessages)

        if chatRoomSchema.item and language_code != "en":
            title = chatRoomSchema.item.title
            description = chatRoomSchema.item.description
            if title:
                chatRoomSchema.item.title = translate_text(title, target_language=language_code, source_language="en")
            if description:
                chatRoomSchema.item.description = translate_text(description, target_language=language_code, source_language="en")

        if chatRoomSchema.last_message_type == 'Offer':
            offer_chats.append(chatRoomSchema)
        else:
            message_chats.append(chatRoomSchema)

        # all_chatRooms.append(chatRoomSchema)

    return {
        "messages": message_chats,
        "offers": offer_chats
    }
    # return all_chatRooms


def get_chat_room(room_data: schemas.GetRoomSchema, current_user: User, db: Session, language_code):
    chatRoomInDb = db.query(models.ChatRoom).filter(
        and_(
            models.ChatRoom.users.contains(room_data.user_id),
            models.ChatRoom.item_id == room_data.item_id
        ) if room_data.item_id else models.ChatRoom.users.contains(room_data.user_id)
    ).first()

    if not chatRoomInDb:
        return None

    roomUsers = json.loads(chatRoomInDb.users)
    roomUsers.remove(current_user.id)
    otherUserId = ''.join(roomUsers)

    chatUserSchema = get_chat_user(otherUserId, db)

    unReadMessages = [message for message in chatRoomInDb.messages if
                      not message.is_read and message.sender_id != current_user.id]

    chatRoomSchema = schemas.ChatRoomInDb.model_validate(chatRoomInDb)
    chatRoomSchema.item = ShopItem.model_validate(chatRoomInDb.item) if chatRoomInDb.item else None
    chatRoomSchema.user = chatUserSchema
    chatRoomSchema.unread_count = len(unReadMessages)

    if chatRoomSchema.item and language_code != "en":
        title = chatRoomSchema.item.title
        description = chatRoomSchema.item.description
        if title:
            chatRoomSchema.item.title = translate_text(title, target_language=language_code, source_language="en")
        if description:
            chatRoomSchema.item.description = translate_text(description, target_language=language_code,
                                                             source_language="en")

    return chatRoomSchema


def get_room_messages(room_id: str, db: Session, current_user: User):
    chatRoomInDb = db.query(models.ChatRoom).filter_by(id=room_id).first()

    if chatRoomInDb:
        mark_as_read(chatRoomInDb.id, db, current_user)
        return [schemas.MessageInDb.model_validate(message) for message in chatRoomInDb.messages]

    else:
        raise UnicornException(
            status_code=status.HTTP_404_NOT_FOUND, message="Room does not exit")


def delete_room(room_list: List[str], db: Session):
    for room_id in room_list:
        roomInDb = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id).first()
        if roomInDb:
            db.delete(roomInDb)
            db.commit()

    raise UnicornException(
        status_code=status.HTTP_200_OK, message="Rooms deleted successfully")


def mark_as_read(room_id: str, db: Session, current_user: User):
    chatRoomInDb = db.query(models.ChatRoom).filter_by(id=room_id).first()
    if not chatRoomInDb:
        raise HTTPException(status_code=404, detail="Chat room not found")

    for message in chatRoomInDb.messages:
        if not message.is_read and message.sender_id != current_user.id:
            message.is_read = True

    db.commit()
    return {"status": "success", "message": "All messages marked as read"}


def get_chat_user(user_id: str, db: Session):
    user = get_user_by_id(user_id, db)

    if not user:
        return None

    userRatingInDb = db.query(UserRatings).filter_by(rated_user_id=user_id).all()
    allUserRating = [rating.value for rating in userRatingInDb]

    chatUserSchema = schemas.ChatUser.model_validate(user.profile)
    chatUserSchema.country = user.profile.country.name
    chatUserSchema.profile_pic = user.profile.profile_pic
    chatUserSchema.profile_pic = chatUserSchema.profile_picture
    chatUserSchema.online = helper.getOnlineStatus(user.last_seen)
    chatUserSchema.last_seen = user.last_seen
    chatUserSchema.average_rating = float(calculate_average(allUserRating))
    chatUserSchema.ratings_count = len(allUserRating)
    chatUserSchema.account_status = user.account_status

    return chatUserSchema
