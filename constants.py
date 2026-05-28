# constants.py
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 365 * 100  # 100 years

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

SESSION_MIDDLEWARE_KEY = os.getenv("SESSION_MIDDLEWARE_KEY")

ALGORITHM = "HS256"

OTP_TOKEN_EXPIRATION_TIME = 500

CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")

CLOUDINARY_SECRET_KEY = os.getenv("CLOUDINARY_SECRET_KEY")

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")

ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID")

ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY")

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

IPINFO_SECRET_KEY = os.getenv("IPINFO_SECRET_KEY")

DEBUG = os.getenv("DEBUG")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "AfcHrb1lZLbaq5toLjghhIDpKH3y4qBp8ghN2ZikXVCeu4U9ytiEVfrgU7onbzkcK4ZwCnH7RJXufC9P")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "EFdLq9Fg55tseMZAiXRGRxssssHYspqSbzj4nGuyKZiCkULcJRm2Cb1Ptyv1DjTZPiRMEBZYqrfZOTag")
PAYPAL_ENV = os.getenv("PAYPAL_ENV", "sandbox")

ALL_PAY_LOGIN_KEY = os.getenv("ALL_PAY_LOGIN_KEY","pp1010950")
ALL_PAY_API_KEY = os.getenv("ALL_PAY_API_KEY", "FF476BDA5335D3C436083FCFC6C1DFCB")
ALL_PAY_PAYMENT_API_URL = os.getenv("ALL_PAY_PAYMENT_API_URL", "https://allpay.to/app/?show=getpayment&mode=api8")
ALL_PAY_WEBHOOK_SECRET = os.getenv("ALL_PAY_WEBHOOK_SECRET", "7D3D00813CE6E5E2DEEF453D4CCB9D05")
HOST = os.getenv("HOST", "http://127.0.0.1:9001")

EMAIL_HOST = os.getenv("EMAIL_HOST", 'cspc186@gmail.com')
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "wwredylgzoaifdct")