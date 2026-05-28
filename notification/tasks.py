from affiliated import models as affiliate_model
from database import SessionLocal
from datetime import datetime, timedelta
from sqlalchemy import cast, Date
from notification import crud, schemas, models
from uuid import uuid4
from notification.manager import notification_manager
from subscription import models, schemas
from notification.crud import send_local_notification, send_push_notification, get_notification_data
from notification.schemas import NotificationType, NotificationBase
import json
from shop.models import ShopItem



def get_user_language(county: str):
    COUNTRY_TO_LANGUAGE = {
        "fr": "fr",
        "il": "he",
        "us": "en",
        "france": "fr",
        "israel": "he",
        "united states": "en"
    }
    return COUNTRY_TO_LANGUAGE.get(county.lower(), "en")


def send_affiliate_expiring_notification():
    db = SessionLocal()
    messages = {
        15: {
            "headings": {
                "en": "15 Days Remaining on Your Affiliate Code",
                "fr": "Il reste 15 jours pour utiliser votre code d'affiliation",
                "he": "נותרו 15 ימים לקוד השותפים שלך"
            },
            "contents": {
                "en": "Your code is still active. Share it now to maximize your rewards before it expires.",
                "fr": "Votre code est toujours actif. Partagez-le dès maintenant pour maximiser vos récompenses avant qu’il n’expire.",
                "he": "הקוד שלך עדיין פעיל. שתף אותו עכשיו כדי למקסם את התגמולים לפני שפג תוקפו."
            }
        },
        7: {
            "headings": {
                "en": "7 Days Left to Earn",
                "fr": "Plus que 7 jours pour gagner",
                "he": "נותרו 7 ימים להרוויח"
            },
            "contents": {
                "en": "One week remaining to benefit from your affiliate code. Don’t miss the opportunity.",
                "fr": "Il ne vous reste qu’une semaine pour profiter de votre code d'affiliation. Ne manquez pas cette opportunité.",
                "he": "נותרה שבוע אחד לנצל את קוד השותפים שלך. אל תפספס את ההזדמנות."
            }
        },
        2: {
            "headings": {
                "en": "2 Days Left — Time’s Running Out",
                "fr": "Plus que 2 jours — Le temps presse",
                "he": "נותרו 2 ימים — הזמן אוזל"
            },
            "contents": {
                "en": "There’s still time to share your code and earn rewards. Act fast.",
                "fr": "Il est encore temps de partager votre code et de gagner des récompenses. Agissez vite.",
                "he": "עדיין אפשר לשתף את הקוד ולהרוויח תגמולים. פעל במהירות."
            }
        },
        0: {
            "headings": {
                "en": "Final Day to Use Your Affiliate Code",
                "fr": "Dernier jour pour utiliser votre code d'affiliation",
                "he": "יום אחרון לשימוש בקוד השותפים שלך"
            },
            "contents": {
                "en": "Your code expires today. Share it now to make the most of it.",
                "fr": "Votre code expire aujourd’hui. Partagez-le maintenant pour en tirer le meilleur parti.",
                "he": "הקוד שלך פג תוקף היום. שתף אותו עכשיו כדי להפיק ממנו את המרב."
            }
        }
    }

    def send_notification(days: int = 0):
        future_date = datetime.utcnow() + timedelta(days=days)
        AffiliateInDb = (
            db.query(affiliate_model.Affiliate).
            filter(cast(affiliate_model.Affiliate.end_date, Date) == future_date.date()).all()
        )
        for affiliate in AffiliateInDb:

            if affiliate.user_id:
                unique_id = str(uuid4())
                notification_model = models.Notifications(
                    id=unique_id,
                    receiver_id=affiliate.user_id,
                    data=json.dumps(messages[days], ensure_ascii=False),
                    type=schemas.NotificationType.Affiliate
                )
                try:
                    db.add(notification_model)
                    db.commit()
                    db.refresh(notification_model)

                    crud.notify_websocket({"type": "newNotification"}, notification_manager, affiliate.user_id)
                except Exception as e:
                    print(e)
                # send push notification
                # lang = get_user_language(affiliate.user.profile.country.name)
                push_data = schemas.NotificationBase(
                    receiver_id=affiliate.user_id,
                    type=schemas.NotificationType.Affiliate
                )
                crud.send_push_notification(
                    push_data=push_data,
                    headings=messages[days]['headings'],
                    subtitle=messages[days]['contents'],
                    contents=messages[days]['contents'],
                    db=db
                )
                print(f"affiliate {days} days notification sent -- {affiliate.code}")
        else:
            print(f"affiliate {days} day not exists.")

    send_notification()
    send_notification(15)
    send_notification(7)
    send_notification(2)

def send_expiring_subscription_notifications():
    db = SessionLocal()
    try:
        three_days = datetime.utcnow() + timedelta(days=3)

        subscriptions = db.query(models.UserSubscription).filter(
            models.UserSubscription.expire_on != None,
            models.UserSubscription.expire_on <= three_days,
            models.UserSubscription.expire_on > datetime.utcnow()
        ).all()

        if len(subscriptions) == 0:
            all_subs = db.query(models.UserSubscription).all()
            for s in all_subs:
                print(f"User:{s.user_id}, Expire:{s.expire_on}")

        for sub in subscriptions:
            template = get_notification_data(NotificationType.expiringSubscriptions)
            notification_data = NotificationBase(
                receiver_id=sub.user_id,
                type=NotificationType.expiringSubscriptions,
                data=json.dumps(template)
            )

            send_local_notification(notification_data, db, sender_id=None)
            send_push_notification(notification_data, template['headings'],template['contents'],db)

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        db.close()

def send_unsold_item_notifications():
    db = SessionLocal()
    try:
        one_month = datetime.utcnow() - timedelta(days=28)
        items = db.query(ShopItem).filter(
            ShopItem.is_sold == False,
            ShopItem.is_active == True,
            ShopItem.date_created <= one_month
        ).all()

        for idx, item in enumerate(items, start=1):
            template = get_notification_data(NotificationType.unsoldItems)
            notification = NotificationBase(
                receiver_id=item.owner_id,
                type=NotificationType.unsoldItems,
                item_id=item.id
            )
            send_local_notification(notification, db, sender_id=None)

            send_push_notification(notification,template['headings'],template['contents'],db)

        db.commit()

    except Exception as e:
        print(f"[ERROR] Unsold item cron failed: {e}")

    finally:
        db.close()



