import asyncio
import json
from typing import List, Optional, Any
from uuid import uuid4

import requests
from requests import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from starlette.background import BackgroundTasks

from I18n.load_language import get_lang_content
from auth.models import User
from constants import ONESIGNAL_API_KEY, ONESIGNAL_APP_ID
from dependency import get_env
from exception import UnicornException
from helper import replace_first
from notification import schemas, models
from notification.manager import notification_manager
from notification.schemas import NotificationType
from shop import schemas as shop_schemas


def send_local_notification(notification_data: schemas.NotificationBase, db: Session,
                            sender_id: Optional[str] = None):
    print(f"=====> Sending local notification to user -> {notification_data.receiver_id} ")
    unique_id = str(uuid4())

    notification_model = models.Notifications(
        id=unique_id,
        receiver_id=notification_data.receiver_id,
        sender_id=sender_id,
        sale_id=notification_data.sale_id,
        type=notification_data.type,
        item_id = notification_data.item_id,
    )

    try:
        db.add(notification_model)
        db.commit()

        notify_websocket({"type": "newNotification"}, notification_manager, notification_data.receiver_id)

    except Exception as e:
        print(e)
        return None

# def send_local_notification(notification_data: schemas.NotificationBase, db: Session,
#                             sender_id: Optional[str] = None):
#     print(f"=====> Sending local notification to user -> {notification_data.receiver_id} ")
#     unique_id = str(uuid4())
#
#     notification_model = models.Notifications(
#         id=unique_id,
#         receiver_id=notification_data.receiver_id,
#         sender_id=sender_id,
#         sale_id=notification_data.sale_id,
#         type=notification_data.type
#     )
#
#     try:
#         db.add(notification_model)
#         db.commit()
#
#         notify_websocket({"type": "newNotification"}, notification_manager, notification_data.receiver_id)
#
#     except Exception as e:
#         print(e)
#         return None


def send_push_notification(push_data: schemas.NotificationBase, headings: dict,
                           contents: dict, db: Session, subtitle: Optional[dict] = None,
                           small_icon: Optional[str] = None):
    print(f"=====> Sending push notification to user -> {push_data.receiver_id} ")

    headers = {
        'Authorization': f'Basic {ONESIGNAL_API_KEY}',
        'accept': 'application/json',
        'content-type': 'application/json',
    }

    json_data = {
        "app_id": f"{ONESIGNAL_APP_ID}",
        "include_aliases": {"external_id": [push_data.receiver_id]},
        "data": {"type": push_data.type, "item_id": push_data.item_id, "chat_id": push_data.chat_id},
        "target_channel": "push",
        "headings": headings,
        "contents": contents,
        "name": "In App Notification"
    }

    if subtitle:
        json_data["subtitle"] = subtitle

    if small_icon:
        json_data["small_icon"] = small_icon

    try:
        response = requests.post('https://onesignal.com/api/v1/notifications', headers=headers, json=json_data)
        print(response)
    except Exception as e:
        return None


def get_notification_data(notification_type: NotificationType, args: Optional[dict] = {}):
    app_env = get_env()
    notification = {
        NotificationType.Welcome: {
            "headings": dict(en=get_translation("en", "welcome to $", [app_env.app_name]),
                             fr=get_translation("fr", "welcome to $", [app_env.app_name]),
                             he=get_translation("he", "welcome to $", [app_env.app_name])),
            "contents": dict(en=get_translation("en", "thank you for joining $ we are excited to have you with us",
                                                [app_env.app_name]),
                             fr=get_translation("fr", "thank you for joining $ we are excited to have you with us",
                                                [app_env.app_name]),
                             he=get_translation("he", "thank you for joining $ we are excited to have you with us",
                                                [app_env.app_name]))
        },
        NotificationType.ItemSale: {
            "headings": dict(en=get_translation("en", "a new purchase from $", [args.get('sender_name', '')]),
                             fr=get_translation("fr", "a new purchase from $", [args.get('sender_name', '')]),
                             he=get_translation("he", "a new purchase from $", [args.get('sender_name', '')])),
            "contents": dict(en=get_translation("en", "purchase your item check it out",
                                                [args.get('sender_name', '')]),
                             fr=get_translation("fr", "purchase your item check it out",
                                                [args.get('sender_name', '')]),
                             he=get_translation("he", "purchase your item check it out",
                                                [args.get('sender_name', '')]))
        },

        NotificationType.ItemShipped: {
            "headings": dict(en=get_translation("en", "item shipped sales id $", [args.get('sale_id', '')]),
                             fr=get_translation("fr", "item shipped sales id $", [args.get('sale_id', '')]),
                             he=get_translation("he", "item shipped sales id $", [args.get('sale_id', '')])),
            "contents": dict(en=get_translation("en", "your order is on its way"),
                             fr=get_translation("fr", "your order is on its way"),
                             he=get_translation("he", "your order is on its way"))
        },

        NotificationType.ItemSaleCompleted: {
            "headings": dict(en=get_translation("en", "sale completed sales id $", [args.get('sale_id', '')]),
                             fr=get_translation("fr", "sale completed sales id $", [args.get('sale_id', '')]),
                             he=get_translation("he", "sale completed sales id $", [args.get('sale_id', '')])),
            "contents": dict(en=get_translation("en", "your item has been successfully sold"),
                             fr=get_translation("fr", "your item has been successfully sold"),
                             he=get_translation("he", "your item has been successfully sold"))
        },
        NotificationType.NewMessage: {
            "headings": {
                "en": "💬 New Message",
                "ar": "💬 رسالة جديدة"
            },
            "subtitle": {
                "en": f"{args.get('sender_name')}",
                "ar": f"{args.get('sender_name')}"
            },
            "contents": {
                "en": f"{args.get('message_content')}",
                "ar": f"{args.get('message_content')}"
            },
            "small_icon": f"{args.get('sender_pic')}"
        },

        NotificationType.NewOffer: {
            "headings": {
                "en": "💬 New Item Offer",
                "ar": "💬 رسالة جديدة"
            },
            "subtitle": {
                "en": f"{args.get('sender_name')}",
                "ar": f"{args.get('sender_name')}"
            },
            "contents": {
                "en": f"{args.get('message_content')}",
                "ar": f"{args.get('message_content')}"
            },
            "small_icon": f"{args.get('sender_pic')}"
        },

        NotificationType.requestResponse: {
            "headings": {
                "en": "New Follow Request",
                "ar": " طلب متابعة جديد"
            },
            "contents": {
                "en": "You have a new follow request",
                "ar": "لديك طلب متابعة جديد"
            }
        },

        NotificationType.expiringSubscriptions: {
            "headings": {
                "en": "Subscription Expiring Soon",
                "ar": " اشتراكك سينتهي قريباً"
            },
            "contents": {
                "en": "Your subscription will expire in a few days. Renew to continue enjoying our services!",
                "ar": "ستنتهي صلاحية اشتراكك خلال أيام قليلة. قم بالتجديد للاستمرار في استخدام خدماتنا!"
            }
        },

        NotificationType.unsoldItems: {
            "headings": {
                "en": "Unsold Item Reminder",
                "ar": "تذكير بعنصر غير مباع"
            },
            "contents": {
                "en": "Your item hasn’t sold in 28 days. Update it or boost its visibility to attract more buyers.",
                "ar": "لم يتم بيع العنصر الخاص بك منذ 28 يومًا. قم بتحديثه أو تعزيز ظهوره لجذب المزيد من المشترين."
            }
        },

        NotificationType.saleNotification: {
            "headings": {
                "en": f"Your item has been sold ",
                "fr": f"Votre article a été vendu ",
                "he": f"הפריט שלך נמכר "
            },
            "contents": {
                "en": f"{args.get('sender_name', 'Someone')} purchased your item. Check order details.",
                "fr": f"{args.get('sender_name', 'Quelqu’un')} a acheté votre article. Vérifiez les détails de la commande.",
                "he": f"{args.get('sender_name', 'מישהו')} קנה את הפריט שלך. בדוק את פרטי ההזמנה."
            }
        },

    }

    return notification[notification_type]


def notify_websocket(json_data: dict, websocket_manager: Any, receiver_id: Optional[str] = None,
                     room_id: Optional[str] = None):
    async def send_websocket_message(websocket):
        await websocket.send_json(json_data)

    async def send_to_websockets():
        tasks = []
        for conn in websocket_manager.active_connections:
            if receiver_id and room_id:
                if conn["user_id"] == receiver_id and conn["room_id"] == room_id:
                    tasks.append(send_websocket_message(conn["websocket"]))

            elif receiver_id:
                if conn["user_id"] == receiver_id:
                    tasks.append(send_websocket_message(conn["websocket"]))
            else:
                tasks.append(send_websocket_message(conn["websocket"]))

        await asyncio.gather(*tasks)

    asyncio.run(send_to_websockets())


def notify_sales_status_change(background_tasks: BackgroundTasks, db: Session,
                               sale_status: shop_schemas.SaleStatus, sale_id: str, receiver_id: str, sender_id: str):
    notificationCreateSchema = None
    if sale_status == shop_schemas.SaleStatus.Shipped:
        notificationCreateSchema = schemas.NotificationBase(
            receiver_id=receiver_id,
            sale_id=sale_id,
            type=schemas.NotificationType.ItemShipped,
        )

    elif sale_status == shop_schemas.SaleStatus.Completed:
        notificationCreateSchema = schemas.NotificationBase(
            receiver_id=receiver_id,
            sale_id=sale_id,
            type=schemas.NotificationType.ItemSaleCompleted,
        )

    else:
        pass

    notificationData = get_notification_data(notificationCreateSchema.type,
                                             {"sale_id": sale_id})

    background_tasks.add_task(send_local_notification, notificationCreateSchema,
                              db, sender_id)

    background_tasks.add_task(send_push_notification, notificationCreateSchema,
                              notificationData.get('headings'), notificationData.get('contents'), db)


def get_user_notification(request: Request, current_user: User, db: Session):
    app_env = get_env()
    lang = request.headers.get('X-language', 'en')

    allUserNotifications = []
    notificationsInDb = db.query(models.Notifications).filter_by(receiver_id=current_user.id).order_by(
        models.Notifications.date_created.desc()).all()

    for notification in notificationsInDb:
        notificationSchema = schemas.NotificationInDb.model_validate(notification)

        if notification.sender_id == "Admin":
            notificationSchema.sender_fullname = app_env.app_name
            notificationSchema.sender_profile_pic = app_env.app_icon

        if notification.sender:
            notificationSchema.sender_fullname = notification.sender.profile.fullname
            notificationSchema.sender_profile_pic = notification.sender.profile.profile_pic
            notificationSchema.sender_profile_pic = notificationSchema.profile_picture

        if notification.type == NotificationType.Welcome:
            notificationData = get_notification_data(NotificationType.Welcome)

        elif notification.type == NotificationType.Affiliate:
            notificationData = json.loads(notification.data)
            notificationSchema.sender_fullname = app_env.app_name
            notificationSchema.sender_profile_pic = app_env.app_icon

        # elif notification.type == NotificationType.ItemSale:
        #     notificationData = get_notification_data(notification.type,
        #                                              {"sender_name": notification.sender.profile.fullname})
        #
        # elif notification.type == NotificationType.ItemShipped or notification.type == NotificationType.ItemSaleCompleted:
        #     notificationData = get_notification_data(notification.type,
        #                                              {"sale_id": notification.sale_id})
        else:
            notificationData = get_notification_data(notification.type)

        notificationSchema.title = notificationData.get('headings').get(lang)
        notificationSchema.subtitle = notificationData.get('contents').get(lang)

        allUserNotifications.append(notificationSchema)

    # allUserNotifications.reverse()

    return allUserNotifications


def mark_as_read(notification_id: str, db: Session):
    notificationInDb = db.query(models.Notifications).filter(models.Notifications.id == notification_id).first()

    if notificationInDb:
        notificationInDb.is_read = True

        db.commit()

    else:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Notification with this id does not exist")


def delete_notification(notification_id: str, db: Session):
    notificationInDb = db.query(models.Notifications).filter(models.Notifications.id == notification_id).first()

    if notificationInDb:
        db.delete(notificationInDb)

        db.commit()

    else:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Notification with this id does not exist")


def get_translation(lang_code: str, key: str, args: Optional[List] = []):
    language_content = get_lang_content(lang_code)

    translation = language_content.get(key)

    for arg in args:
        trans_data = replace_first(language_content.get(key), "$", arg)
        translation = trans_data

    return translation
