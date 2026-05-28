import re
from uuid import uuid4

import pyotp
import requests
from dotenv import load_dotenv
from firebase_admin import auth
from firebase_admin.auth import InvalidIdTokenError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy_utils import Country
from starlette import status
from starlette.background import BackgroundTasks
from starlette.requests import Request

import main
from I18n.load_language import get_lang_content
from auth import schemas, models
from constants import pwd_context, OTP_TOKEN_EXPIRATION_TIME, DEBUG
from exception import credentials_exception, UnicornException
from helper import create_access_token
from notification import crud as notification_crud
from notification import schemas as notification_schemas
from preferences import crud as pref_crud
from profile import crud as profile_crud
from profile import schemas as profile_schemas
import logging
from fastapi import status  # Assuming you're using FastAPI

# Load .env file
load_dotenv()


async def social_auth(request: Request, access_token: str, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    try:
        ip_address = request.headers.get("X-Real-IP")
        user_geo = get_geolocation(ip_address)

        decoded_token = auth.verify_id_token(access_token)
        provider = decoded_token['firebase']['sign_in_provider']
        user_email = decoded_token.get('email', 'No email provided')
        user_full_name = decoded_token.get('name', '')
        profile_pic = decoded_token.get('picture', '')

        if provider == "google.com":
            sign_in_provider = schemas.AuthProvider.Google
        elif provider == "apple.com":
            sign_in_provider = schemas.AuthProvider.Apple
        elif provider == "facebook.com":
            sign_in_provider = schemas.AuthProvider.Facebook
        else:
            sign_in_provider = None

        userInDb = db.query(models.User).filter(models.User.email_address == user_email).first()

        if not userInDb:
            unique_id = str(uuid4())
            db_user = models.User(id=unique_id, email_address=user_email,
                                  is_email_verified=True, auth_provider=sign_in_provider)
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            await profile_crud.setup_user_profile(
                request,
                profile_schemas.Profile(
                    id=db_user.id,
                    fullname=user_full_name,
                    username=generate_username(db_user.email_address.replace("@gmail.com", "")),
                    country=user_geo.get('country'),
                    address=f"{Country(user_geo.get('country')).name}, {user_geo.get('city')}"
                ),
                db
            )

            await pref_crud.set_up_user_pref(db_user.id, db)

            access_token = create_access_token(db_user.email_address)

            user_schema = profile_crud.get_user_profile_schema(db_user, db)

            return {"message": language_content.get('account created successfully'),
                    "user": user_schema, "status": True,
                    "is_verified": db_user.is_email_verified,
                    "access_token": access_token}
        else:

            profileSchema = profile_crud.get_user_profile_schema(userInDb, db)

            access_token = create_access_token(userInDb.email_address)

            return {"message": language_content.get('account logged in successfully'),
                    "user": profileSchema, "is_verified": userInDb.is_email_verified,
                    "access_token": access_token, "status": True}

    except InvalidIdTokenError:
        raise credentials_exception


async def create_user(request: Request, user_data: schemas.CreateUser, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    unique_id = str(uuid4())
    userDict = user_data.model_dump()
    userDict['id'] = unique_id
    userDict['password'] = get_password_hash(user_data.password)
    userDict['auth_provider'] = schemas.AuthProvider.Email
    userDict.pop('fullname')
    nickname = userDict.pop("nickname")
    company_name = userDict.pop("comapny_name", '')
    company_registration_num = userDict.pop("company_registration_num", "")
    userModel = models.User(**userDict)
    userInDb = db.query(models.User).filter_by(email_address=userModel.email_address).first()

    if userInDb:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message=language_content.get('user with this email address already exists'))

    ip_address = request.headers.get("X-Real-IP")
    user_geo = get_geolocation(ip_address)

    db.add(userModel)
    db.commit()
    db.refresh(userModel)

    await profile_crud.setup_user_profile(
        request,
        profile_schemas.Profile(
            id=userModel.id,
            fullname=user_data.fullname,
            username=generate_username(user_data.email_address.replace("@gmail.com", "")),
            country=user_geo.get('country'),
            address=f"{Country(user_geo.get('country')).name}, {user_geo.get('city')}",
            nickname=nickname,
            company_name=company_name,
            company_registration_num=company_registration_num
        ),
        db
    )

    await pref_crud.set_up_user_pref(userModel.id, db)

    access_token = create_access_token(userModel.email_address)

    user_schema = profile_crud.get_user_profile_schema(userModel, db)

    return {"message": language_content.get('account created successfully'),
            "user": user_schema, "status": True,
            "is_verified": userModel.is_email_verified,
            "access_token": access_token}


def login_user(request: Request, data: schemas.UserLogin, db: Session):
    userInDb = db.query(models.User).filter_by(email_address=data.email_address).first()
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    if not userInDb:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message=language_content.get('email or password is incorrect'))

    if userInDb.account_status != schemas.AccountStatus.Enabled:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message=language_content.get('your account had been $').replace('$',
                                                                                               language_content.get(
                                                                                                   userInDb.account_status,
                                                                                                   '')))

    if not verify_password(plain_password=data.password, hashed_password=userInDb.password):
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message=language_content.get('email or password is incorrect'))

    profileSchema = profile_crud.get_user_profile_schema(userInDb, db)
    # print("profileSchema", profileSchema.is_seller)
    access_token = create_access_token(userInDb.email_address)

    return {"message": language_content.get('account logged in successfully'),
            "user": profileSchema, "is_verified": userInDb.is_email_verified,
            "access_token": access_token, "status": True}


def request_otp_code(request: Request, email_address: str, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    new_otp_secret = pyotp.random_base32(length=32)
    userInDb = get_user(email_address, db)

    if not userInDb:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message=language_content.get('user with email not found'))

    userInDb.otp_secret = new_otp_secret
    db.commit()

    otp_secret = userInDb.otp_secret
    otp = pyotp.TOTP(otp_secret, digits=4, interval=OTP_TOKEN_EXPIRATION_TIME)
    otp_code = otp.now()

    # if DEBUG:
    print(f"Otp code =======> {otp_code}")
    # return True

    # response = send_otp_email(userInDb.email_address, otp_code, userInDb.profile.fullname)
    # print(response)
    # if response.status_code != status.HTTP_200_OK:
    #     raise UnicornException(status_code=status.HTTP_408_REQUEST_TIMEOUT,
    #                            message=language_content.get('cant send otp'))

    is_sent = send_otp_email(
        userInDb.email_address,
        otp_code,
        userInDb.profile.fullname
    )

    if not is_sent:
        raise UnicornException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            message=language_content.get('cant send otp')
        )

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message=language_content.get('otp sent successfully'))


def verify_account(background_tasks: BackgroundTasks, request: Request, data: dict, db: Session):
    result = verify_otp_code(request, data.get('email_address'), data.get('otp_code'), db)

    if result.get('status'):
        lang = request.headers.get('X-language', 'en')
        language_content = get_lang_content(lang)

        user = get_user(data.get('email_address'), db)

        if user.is_email_verified:
            raise UnicornException(status_code=status.HTTP_226_IM_USED,
                                   message=language_content.get('account verified already'))

        user.is_email_verified = True
        db.commit()

        notificationCreateSchema = notification_schemas.NotificationBase(
            receiver_id=user.id,
            type=notification_schemas.NotificationType.Welcome,
        )

        background_tasks.add_task(notification_crud.send_local_notification, notificationCreateSchema, db, "Admin")

        return {"message": language_content.get('account verified successfully'), "status": True}


def verify_otp_code(request: Request, email_address: str, otp_code: str, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    user = get_user(email_address, db)
    if not user:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message=language_content.get('user with email not found'))

    otp = pyotp.TOTP(user.otp_secret, digits=4, interval=OTP_TOKEN_EXPIRATION_TIME)
    if not otp.verify(otp_code, valid_window=1):
        raise UnicornException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                               message=language_content.get('invalid otp code'))

    return {"status": True, "message": language_content.get('valid otp code'), "otp_secret": user.otp_secret}


def reset_password(request: Request, data: dict, db):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    email_address = data.get("email_address")
    secret_code = data.get("secret_code")
    new_password = data.get("new_password")
    user = get_user(email_address, db)

    if not user:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message=language_content.get('user with email not found'))

    if user.otp_secret == secret_code:
        user.password = get_password_hash(new_password)
        db.commit()
        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('password reset successfully'))
    else:
        raise UnicornException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                               message=language_content.get('opt secret invalid'))


def change_password(request: Request, current_user: models.User, data: dict, db: Session):
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    if verify_password(old_password, current_user.password):
        current_user.password = get_password_hash(new_password)
        db.commit()

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('password changed successfully'))
    else:
        raise UnicornException(status_code=status.HTTP_403_FORBIDDEN,
                               message=language_content.get('old password incorrect'))


def generate_username(full_name):
    if len(full_name) != 0:
        names = full_name.split()
        first_initial = names[0][0].lower() if names and names[0] else ''
        username = '@' + first_initial + names[-1].lower() if names and names[-1] else ''
        username = re.sub(r'[^a-zA-Z0-9]', '', username)
        username = '@' + username[:9].ljust(9, 'x')  # ljust pads with 'x' if the length is less than 9
        return username
    return full_name

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from constants import EMAIL_HOST, EMAIL_PASSWORD


def send_otp_email(email_address, otp_code, fullname):
    sender_email = EMAIL_HOST
    sender_password = EMAIL_PASSWORD
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    subject = "Your OTP Code"
    body = f"""
Hello {fullname},

Your OTP code is: {otp_code}

This OTP will expire in 2 minutes.

Thanks,
Sold App Team
"""

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email_address, msg.as_string())
        server.quit()
        return True

    except Exception as e:
        print("SMTP Error:", e)
        return False



def get_geolocation(ip_address: str):
    details = main.ipinfo_handler.getDetails(ip_address)
    return {
        "city": details.city,
        "country": details.country
    }


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(email_address: str, db: Session):
    return db.query(models.User).filter_by(email_address=email_address).first()


def get_user_by_id(user_id: str, db: Session):
    return db.query(models.User).filter(models.User.id == user_id).first()


def authenticate_user(email_address: str, password: str, db: Session):
    user = db.query(models.User).filter_by(email_address=email_address).first()
    if not user or user.account_status == schemas.AccountStatus.Deleted:
        return None
    else:
        if user.auth_provider == schemas.AuthProvider.Email:
            if not verify_password(password, user.password):
                return None
            return user
