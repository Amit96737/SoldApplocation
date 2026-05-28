from sqlalchemy.orm import Session
from . import models, schemas, crud
from starlette.requests import Request
from jose import jwt
from constants import SECRET_KEY, ALGORITHM, oauth2_scheme
from shop import models as shop_models
from auth import crud as auth_crud, models as auth_models, schemas as auth_schemas
from fastapi import Depends
from dependency import get_db
from fastapi import HTTPException, status
from sqlalchemy import func
from datetime import datetime, timedelta
from jose import jwt, JWTError
from exception import credentials_exception


def get_admin(email_address: str, db: Session):
    return db.query(models.Administrator).filter(models.Administrator.email_address == email_address).first()


def get_admin_profile(user: models.Administrator):
    adminInDbSchema = schemas.AdminInDb.model_validate(user)
    adminInDbSchema.profile_pic = adminInDbSchema.profile_picture
    return adminInDbSchema


async def get_current_admin(request: Request, db: Session):
    try:
        token = request.cookies.get('access_token')
        if token is None:
            return None
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        email_address: str = payload.get("sub")
        current_admin = get_admin(email_address, db)
        if not current_admin:
            return None
        return get_admin_profile(current_admin)

    except Exception as e:
        print(e)
        return None


def authenticate_admin_user(email_address: str, password: str, db: Session):
    user = get_admin(email_address, db)
    if not user:
        return None
    if not auth_crud.verify_password(password, user.password):
        return None
    return user


def delete_favourited_items(user_id: int, all_favourited_shop_items: list, db: Session = Depends(get_db)):
    item_ids = [favourited_item.item_id for favourited_item in all_favourited_shop_items]

    items_to_delete = (
        db.query(shop_models.ShopItem)
        .filter(shop_models.ShopItem.id.in_(item_ids), shop_models.ShopItem.owner_id == user_id)
        .all()
    )

    for item in items_to_delete:
        print(item.owner.email_address)
        db.delete(item)

    db.commit()


async def require_login(request: Request, db: Session = Depends(get_db)):
    user = await get_current_admin(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Redirecting to login",
            headers={"Location": "/admin/login"}
        )
    return user


def get_active_posters(db: Session):
    cutoff_date = datetime.utcnow() - timedelta(days=14)

    subquery = (
        db.query(
            shop_models.ShopItem.owner_id,
            func.count(shop_models.ShopItem.id).label("item_count")
        )
        .filter(shop_models.ShopItem.date_created >= cutoff_date)
        .group_by(shop_models.ShopItem.owner_id)
        .having(func.count(shop_models.ShopItem.id) >= 10)
        .subquery()
    )

    # Optionally, return user info too
    active_user_ids = db.query(subquery.c.owner_id).all()
    return [uid for (uid,) in active_user_ids]


async def get_admin_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email_address: str = payload.get("sub")
        if email_address is None:
            raise credentials_exception
        token_data = email_address
    except JWTError:
        raise credentials_exception
    current_admin = get_admin(email_address, db)

    if not current_admin:
        return None

    return current_admin

