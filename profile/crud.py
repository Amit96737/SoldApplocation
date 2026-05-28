from typing import Optional, Any

from firebase_admin import auth
from pydantic_core.core_schema import AnySchema
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy_utils import Country
from starlette import status
from starlette.requests import Request
import helper
from I18n.load_language import get_lang_content
from auth import models as auth_models
from auth.models import User
from exception import UnicornException
from helper import calculate_average
from preferences import models as pref_models
from profile import schemas, models
from auth.schemas import AccountStatus
from ratings import models as ratings_models
from subscription import crud as subscription_crud

from uuid import uuid4
from notification import crud as notification_crud
from starlette.background import BackgroundTasks
from notification.crud import get_notification_data, send_local_notification, send_push_notification
from notification.schemas import NotificationType, NotificationBase
import json

def get_profile_by_id(request: Request, user_id: str, db: Session, current_user_id: Optional[str] = ""):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    userInDb = db.query(auth_models.User).filter_by(id=user_id).first()

    if not userInDb or userInDb.account_status != AccountStatus.Enabled:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('user with id not found'))

    user_schema = get_user_profile_schema(userInDb, db, current_user_id)
    return user_schema


async def setup_user_profile(request: Request, profile_data: schemas.Profile, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    profileDict = profile_data.model_dump()
    profileDict['country'] = Country(profile_data.country)
    print("profileDict ", profileDict)

    userProfileModel = models.Profile(**profileDict)

    try:
        db.add(userProfileModel)
        db.commit()
        db.refresh(userProfileModel)

        return userProfileModel

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message=language_content.get('user profile already exists'))


def edit_user_profile(request: Request, profile_data: schemas.ProfileEdit, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    print(profile_data)

    userProfileInDb = db.query(models.Profile).filter_by(id=current_user.id).first()
    userInDb = db.query(auth_models.User).filter_by(id=current_user.id).first()
    userPrefsInDb = db.query(pref_models.Preference).filter_by(user_id=current_user.id).first()

    profileData = profile_data.model_dump(exclude_unset=True)

    if profileData.get('country'):
        try:
            userProfileInDb.country = Country(profileData.get('country'))
            profileData.pop('country')

        except Exception as e:
            print(e)

    if profileData.get('show_notification'):
        userPrefsInDb.show_notification = profileData.get('show_notification')
        profileData.pop('show_notification')

    if profileData.get('holiday_mode') is not None:
        userPrefsInDb.holiday_mode = profileData.get('holiday_mode')
        profileData.pop('holiday_mode')

    if profileData.get('phone_number'):
        userInDb.phone_number = profileData.get('phone_number')
        userInDb.is_number_verified = True
        try:
            user = auth.get_user_by_phone_number(profileData.get('phone_number'))
            auth.delete_user(user.uid)
            profileData.pop('phone_number')

        except Exception as e:
            print(e)

    if userProfileInDb:
        for key, value in profileData.items():
            print(key, value)
            setattr(userProfileInDb, key, value)

    db.commit()

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message=language_content.get('user profile updated successfully'))

def follow_user(request: Request, user_id: str, current_user: User, db: Session, background_tasks: BackgroundTasks):

    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    userInDb = db.query(auth_models.User).filter_by(id=user_id).first()
    if not userInDb or userInDb.account_status != AccountStatus.Enabled:
        raise UnicornException(status_code=404, message=language_content.get('user with id not found'))

    if user_id == current_user.id:
        raise UnicornException(status_code=403, message=language_content.get('you cannot follow yourself'))

    notification_template = get_notification_data(NotificationType.requestResponse)

    if userInDb not in current_user.following:
        current_user.following.append(userInDb)
        db.commit()
        db.refresh(current_user)

        notification_data = NotificationBase(
            receiver_id=userInDb.id,
            type=NotificationType.requestResponse
        )
        background_tasks.add_task(send_local_notification, notification_data, db, current_user.id)
        background_tasks.add_task(
            send_push_notification,
            notification_data,
            notification_template['headings'],
            notification_template['contents'],
            db
        )
        if current_user in userInDb.following:
            notification_data_back = NotificationBase(
                receiver_id=current_user.id,
                type=NotificationType.requestResponse
            )
            background_tasks.add_task(send_local_notification, notification_data_back, db, userInDb.id)
            background_tasks.add_task(
                send_push_notification,
                notification_data_back,
                notification_template['headings'],
                notification_template['contents'],
                db
            )

        return {
            "status": True,
            "message": language_content.get('you are now following this user')
        }

    else:
        current_user.following.remove(userInDb)
        db.commit()
        db.refresh(current_user)

        raise UnicornException(status_code=200, message=language_content.get('you unfollowed this user'))

# def accept_follow_request(request: Request, request_id: str, current_user: User, db: Session):
#     lang = request.headers.get('X-language', 'en')
#     language_content = get_lang_content(lang)
#
#     follow_request = db.query(FollowRequest).filter_by(
#         id=request_id,
#         receiver_id=current_user.id,
#         status="pending"
#     ).first()
#
#     if not follow_request:
#         raise UnicornException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             message=language_content.get("Follow request not found"))
#
#     follow_request.status = "accepted"
#
#     sender = db.query(User).filter_by(id=follow_request.sender_id).first()
#     current_user.following.append(sender)
#
#     db.commit()
#
#     notificationCreateSchema = NotificationBase(
#         receiver_id=sender.id,
#         type=NotificationType.RequestResponse
#     )
#
#     notificationData = notification_crud.get_notification_data(
#         NotificationType.RequestResponse,
#         {"message": "Your follow request was accepted"}
#     )
#
#     notification_crud.send_push_notification(
#         notificationCreateSchema,
#         notificationData.get('headings'),
#         notificationData.get('contents'),
#         db
#     )
#     return {"message": "Follow request accepted"}
#
# def reject_follow_request(request: Request, request_id: str, current_user: User, db: Session):
#     lang = request.headers.get('X-language', 'en')
#     language_content = get_lang_content(lang)
#
#     follow_request = db.query(FollowRequest).filter_by(
#         id=request_id,
#         receiver_id=current_user.id,
#         status="pending"
#     ).first()
#
#     if not follow_request:
#         raise UnicornException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             message=language_content.get("Follow request not found"))
#
#     follow_request.status = "rejected"
#     db.commit()
#
#     notificationCreateSchema = NotificationBase(
#         receiver_id=follow_request.sender_id,
#         type=NotificationType.RequestResponse
#     )
#
#     notificationData = notification_crud.get_notification_data(
#         NotificationType.RequestResponse,
#         {"message": "Your follow request was rejected"}
#     )
#
#     notification_crud.send_push_notification(
#         notificationCreateSchema,
#         notificationData.get('headings'),
#         notificationData.get('contents'),
#         db
#     )
#
#     return {"message": "Follow request rejected"}
from subscription.models import UserSubscription
def get_user_profile_schema(user, db, current_user_id: Optional[str] = ""):
    # print("get_user_profile_schema")
    user_pref = db.query(pref_models.Preference).filter_by(user_id=user.id).first()
    followers = user.followed_by
    ratingsInDb = db.query(ratings_models.UserRatings).filter_by(rated_user_id=user.id).all()
    allUserRating = [rating.value for rating in ratingsInDb]

    profileSchema = schemas.ProfileInDb.model_validate(user)
    profileSchema.fullname = user.profile.fullname
    profileSchema.nickname = user.profile.nickname if user.profile.nickname else ""
    profileSchema.address = user.profile.address
    profileSchema.country = user.profile.country.name
    profileSchema.username = user.profile.username
    profileSchema.company_name = user.profile.company_name
    profileSchema.company_registration_num = user.profile.company_registration_num
    profileSchema.profile_pic = user.profile.profile_pic
    profileSchema.profile_pic = profileSchema.profile_picture
    profileSchema.about = user.profile.about
    profileSchema.average_rating = float(calculate_average(allUserRating))
    profileSchema.ratings_count = len(allUserRating)
    profileSchema.last_seen = user.last_seen
    profileSchema.sex = user.profile.sex
    profileSchema.online = helper.getOnlineStatus(user.last_seen)
    profileSchema.show_location = user_pref.show_location
    profileSchema.show_notification = user_pref.show_notification
    profileSchema.holiday_mode = user_pref.holiday_mode
    profileSchema.favorite_items = [item.id for item in user.favourited_items]
    profileSchema.followers = [user.id for user in followers]
    profileSchema.items_count = len(
        [item for item in user.shop_items if not item.is_sold]) if current_user_id != user.id else (
        len([item for item in user.shop_items]))
    profileSchema.following = [user.id for user in user.following]
    profileSchema.favorited_topics = [topic.id for topic in user.favorited_topics]

    profileSchema.is_seller = user.is_seller

    subscriptions = subscription_crud.get_active_subscription(db, user.id)
    # print("subscriptions", subscriptions)
    profileSchema.subscriptions = subscriptions

    return profileSchema


def get_all_user_profiles(request: Request, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    usersInDb = db.query(auth_models.User).filter(auth_models.User.account_status == AccountStatus.Enabled).all()

    if not usersInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('no users found', 'No users found'))

    user_profiles = [get_user_profile_schema(user, db) for user in usersInDb]
    return user_profiles


def get_followers_users(user: User, db: Session, user_id, query):
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UnicornException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Invalid user doesn't exists"
            )
    followers_users = user.followed_by
    if query:
        followers_users = [
            followed_user for followed_user in user.following
            if query.lower() in followed_user.profile.fullname.lower()
        ]

    following = [get_user_profile_schema(user=user, db=db) for user in followers_users]
    return following


def get_user_following(user: User, db: Session, user_id, query):
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UnicornException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Invalid user doesn't exists"
            )

    following_users = user.following
    if query:
        following_users = [
            followed_user for followed_user in user.following
            if query.lower() in followed_user.profile.fullname.lower()
        ]

    following = [get_user_profile_schema(user=user, db=db) for user in following_users]
    return following
