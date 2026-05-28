import cloudinary
import firebase_admin
import ipinfo
from fastapi import FastAPI, HTTPException
from fastapi_sqlalchemy import DBSessionMiddleware
from firebase_admin import credentials
from requests import Request
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from admin import main as admin_main, models as admin_models
from appconfig import main as config_main
from appconfig.schemas import AppEnv
from auth import main as auth_main, models as auth_models
from chats import main as chats_main, models as chats_models
from cms import models as cms_models, main as cms_main
from constants import oauth2_scheme
from database import SQLALCHEMY_DATABASE_URL, engine, SessionLocal
from dependency import get_current_user
from exception import UnicornException
from forum import main as forum_main, models as forum_models
from notification import main as notification_main, models as notification_models
from payment import main as payment_main, models as payment_models
from preferences import models as preferences_models
from profile import main as profile_main, models as profile_models
from ratings import main as ratings_main, models as ratings_models
from search import main as search_main, models as search_models
from shippings import main as shipping_main, models as shipping_models
from shop import main as shop_main, models as shop_models, tasks as shop_task
from socialmedia import models as social_media_models
from subscription import models as subscription_models, main as subscription_main
from others import models as others_models, main as others_main
from affiliated import models as affiliated_models, main as affiliate_main, tasks as affiliate_task
from notification.tasks import *
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from logging.handlers import RotatingFileHandler
from fastapi import Query
from notification import tasks as notification_tasks
from shop.crud import LanguageMiddleware

app_env = AppEnv()  # Global variable

app = FastAPI(
    title=f"{app_env.app_name} Endpoints",
    summary="Sold App Api Endpoints Built by Tosin Peter",
    version="1.0.0"
)

app.add_middleware(LanguageMiddleware)
app.add_middleware(GZipMiddleware)
app.add_middleware(SessionMiddleware, secret_key=app_env.session_middleware_key)
app.add_middleware(DBSessionMiddleware, db_url=SQLALCHEMY_DATABASE_URL)


app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up CORS configuration
origins = [
    "http://localhost"
    "https://dfordirect.com"
    "https://backend-sold.vercel.app/",
    "http://127.0.0.1:5500",
    "*"
]

# CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase
# cred = credentials.Certificate("serviceAccountKey.json")
# firebase_admin.initialize_app(cred)

# Initialize Cloudinary
cloudinary.config(
    cloud_name=app_env.cloudinary_cloud_name,
    api_key=app_env.cloudinary_api_key,
    api_secret=app_env.cloudinary_secret_key
)

# Initialize the ipinfo handler
ipinfo_handler = ipinfo.getHandler(access_token=app_env.ipinfo_secret_key)

# logger

import os
os.makedirs("logs", exist_ok=True)

log_file = "logs/app.log"
handler = RotatingFileHandler(
    log_file, maxBytes=5 * 1024 * 1024, backupCount=3  # 5MB max, keep 3 backups
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[handler, logging.StreamHandler()]
)


def reinitialize_app_env():
    global app_env
    app_env = AppEnv()


@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "status": exc.status_code == status.HTTP_200_OK},
    )


@app.middleware("http")
async def update_last_seen_middleware(request: Request, call_next):
    response = await call_next(request)
    try:
        token = await oauth2_scheme(request)
        if token:
            db = SessionLocal()
            try:
                get_current_user(token, db)
            finally:
                db.close()

    except HTTPException:
        return response

    return response


@app.get("/.well-known/assetlinks.json")
async def deep_link():
    return [{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.tech.sold",
    "sha256_cert_fingerprints":
    ["2D:80:27:BA:7D:C4:68:04:6D:89:CC:2C:E2:3A:D9:B0:5A:F4:1C:4F:24:79:0A:1F:AC:71:C7:A4:E3:69:E9:31"]
  }
}]


@app.get("/.well-known/apple-app-site-association")
async def apple_deep_link():
    return {
        "applinks": {
            "apps": [],
            "details": [
            {
                "appIDs": "DVQQB45T3T.com.tech.sold",
                "paths": [ "/shop/item/*", "/" ]
            }
            ]
        }
    }


admin_models.Base.metadata.create_all(bind=engine)
auth_models.Base.metadata.create_all(bind=engine)

profile_models.Base.metadata.create_all(bind=engine)
preferences_models.Base.metadata.create_all(bind=engine)
shipping_models.Base.metadata.create_all(bind=engine)
payment_models.Base.metadata.create_all(bind=engine)
shop_models.Base.metadata.create_all(bind=engine)
forum_models.Base.metadata.create_all(bind=engine)
social_media_models.Base.metadata.create_all(bind=engine)
chats_models.Base.metadata.create_all(bind=engine)
search_models.Base.metadata.create_all(bind=engine)
ratings_models.Base.metadata.create_all(bind=engine)
notification_models.Base.metadata.create_all(bind=engine)
cms_models.Base.metadata.create_all(bind=engine)
affiliated_models.Base.metadata.create_all(bind=engine)
subscription_models.Base.metadata.create_all(bind=engine)
others_models.Base.metadata.create_all(bind=engine)

app.include_router(config_main.router, prefix="/api/v1")
app.include_router(cms_main.router, prefix='/api/v1')
app.include_router(auth_main.router, prefix="/api/v1")
app.include_router(profile_main.router, prefix="/api/v1")
app.include_router(shop_main.router, prefix='/api/v1')
app.include_router(shipping_main.router, prefix='/api/v1')
app.include_router(payment_main.router, prefix='/api/v1')
app.include_router(forum_main.router, prefix='/api/v1')
app.include_router(chats_main.router, prefix='/api/v1')
app.include_router(search_main.router, prefix='/api/v1')
app.include_router(ratings_main.router, prefix='/api/v1')
app.include_router(notification_main.router, prefix='/api/v1')
app.include_router(subscription_main.router, prefix='/api/v1')
app.include_router(others_main.router, prefix='/api/v1')
app.include_router(affiliate_main.router, prefix='/api/v1')
app.include_router(admin_main.router)

# task

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    # scheduler.add_job(send_affiliate_expiring_notification, "interval", seconds=10)
    scheduler.add_job(send_affiliate_expiring_notification, "cron", hour=9, minute=30)
    scheduler.add_job(affiliate_task.deactivate_affiliate_code_expire, "interval",  minutes=60)
    scheduler.add_job(shop_task.deactivate_expired_item_boosts, "interval",  minutes=60)

    scheduler.add_job(notification_tasks.send_expiring_subscription_notifications, trigger="interval", hours=24)
    scheduler.add_job(notification_tasks.send_unsold_item_notifications, trigger="interval", hours=24)
    scheduler.start()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()


@app.get("/shop/item/detail", tags=["Shop"])
async def get_item_details_by_id(
    item_id: str = Query(...)
):
    from fastapi.responses import HTMLResponse
    html_content = f"""
    <html>
        <head>
            <meta http-equiv="refresh" content="0;url=myapp://shop/item/detail?item_id={item_id}" />
            <script>
                window.location.href = "sold.csdevhub.com://shop/item/detail?item_id={item_id}";
                setTimeout(function() {{
                    window.location.href = "https://play.google.com/store/apps/details?id=com.tech.sold";
                }}, 2000);
            </script>
        </head>
        <body>
            <p>Redirecting to app...</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)





