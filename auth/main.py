from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks
from starlette.requests import Request

from auth import crud, schemas, models
from dependency import get_db, get_current_user

router = APIRouter(
    prefix="/auth",
)


@router.post("/social-auth", tags=["Social Auth"])
async def social_auth(request: Request, data: dict = {'access_token': ''}, db: Session = Depends(get_db)):
    socialAuth = await crud.social_auth(request, data.get('access_token'), db)
    return socialAuth


@router.post("/register", tags=["Auth"])
async def register_user(request: Request, user_data: schemas.CreateUser, db: Session = Depends(get_db)):
    result = await crud.create_user(request, user_data, db)
    return result


@router.post("/login", tags=["Auth"])
async def login_user(request: Request, data: schemas.UserLogin, db: Session = Depends(get_db)):
    return crud.login_user(request, data, db)


@router.post("/request-otp-code", tags=["Auth"])
async def send_verification_code(request: Request, data: dict = {"email_address": "tester@gmail.com"},
                                 db: Session = Depends(get_db)):
    return crud.request_otp_code(request, data.get('email_address'), db)


@router.post("/verify-account", tags=["Auth"])
async def verify_user_account(background_tasks: BackgroundTasks, request: Request, data: dict = {"email_address": "tester@gmail.com", "otp_code": "1234"},
                              db: Session = Depends(get_db)):
    return crud.verify_account(background_tasks, request, data, db)


@router.post("/verify-otp-code", tags=["Auth"])
async def verify_otp_code(request: Request, data: dict = {"email_address": "tester@gmail.com", "otp_code": "1234"},
                          db: Session = Depends(get_db)):
    return crud.verify_otp_code(request, data.get('email_address'), data.get('otp_code'), db)


@router.post("/reset-password", tags=["Auth"])
async def reset_password(request: Request,
                         data: dict = {"email_address": "tester@gmail.com", "secret_code": "12345",
                                       "new_password": "password"},
                         db: Session = Depends(get_db)):
    return crud.reset_password(request, data, db)


@router.post("/change-password", tags=["Auth"])
async def change_password(request: Request,
                          data: dict = {"old_password": "string", "new_password": "password"},
                          current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.change_password(request, data, current_user, db)


