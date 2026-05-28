import time

from sqlalchemy import select, and_
from auth.models import favourited_items, AppOpen
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from shop.models import Brands
from uuid import uuid4
from sqlalchemy import or_, and_
from shop.models import ShopItem


def is_favorited(db: Session, user_id: str, item_id: str) -> bool:
    stmt = select(favourited_items).where(
        and_(
            favourited_items.c.user_id == user_id,
            favourited_items.c.item_id == item_id
        )
    )
    result = db.execute(stmt).first()
    return result is not None


def insert_log_app_open(db: Session, user):
    today = datetime.utcnow().date()

    existing_open = (
        db.query(AppOpen)
        .filter(
            AppOpen.user_id == user.id,
            func.date(AppOpen.opened_at) == today
        )
        .first()
    )

    if not existing_open:
        new_open = AppOpen(user_id=user.id)
        db.add(new_open)
        db.commit()

    print("-----complete app log task-----")

def get_or_create_brand(db: Session, brand_name: str):
    brand_name = brand_name.strip().capitalize()
    brand = db.query(Brands).filter(
        Brands.name == brand_name
    ).first()

    if not brand:
        brand = Brands(
            id=str(uuid4()),
            name=brand_name,
            enabled=True,
            featured=False
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)

    return brand

def sold_item_visibility(query):
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    return query.filter(
        or_(
            ShopItem.is_sold == False,
            and_(
                ShopItem.is_sold == True,
                ShopItem.date_created >= seven_days_ago
            )
        )
    )
