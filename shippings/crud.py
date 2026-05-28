from uuid import uuid4
from sqlalchemy import case

from sqlalchemy.orm import Session
from starlette import status

from I18n.load_language import get_lang_content
from exception import UnicornException
from shippings import schemas, models
from auth.models import User
from starlette.requests import Request
from shop import models as shop_model


def modify_shipping_details(request: Request, shipping_info: schemas.ShippingEdit, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    shippingInfoInDb = db.query(models.ShippingInfo).filter(models.ShippingInfo.user_id == current_user.id).first()

    if shippingInfoInDb:
        for field, value in shipping_info.model_dump(exclude_unset=True).items():
            setattr(shippingInfoInDb, field, value)

        db.commit()

        shippingInfoInDb = db.query(models.ShippingInfo).filter(models.ShippingInfo.user_id == current_user.id).first()

        return {
            "message": language_content.get('shipping info updated successfully'),
            "status": True,
            "data": shippingInfoInDb
        }

    else:
        unique_id = str(uuid4())
        shippingModel = models.ShippingInfo(
            id=unique_id,
            address=shipping_info.address,
            user_id=current_user.id,
            city=shipping_info.city,
            zip_code=shipping_info.zip_code
        )

        db.add(shippingModel)
        db.commit()
        db.refresh(shippingModel)

        return {
            "message": language_content.get('shipping info updated successfully'),
            "status": True,
            "data": shippingModel
        }


def get_shipping_info(current_user: User, db: Session):
    shippingInfoInDb = db.query(models.ShippingInfo).filter(models.ShippingInfo.user_id == current_user.id).first()
    if shippingInfoInDb:
        return shippingInfoInDb

    else:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="No shipping address found for this user")


def user_shipping_info(current_user: User, db: Session):
    shippingInfoInDb = db.query(models.ShippingInfo).filter(models.ShippingInfo.user_id == current_user.id).first()
    if shippingInfoInDb:
        return shippingInfoInDb
    return None


def user_near_pickup_points(user: User, db: Session):
    address_parts = user.profile.address.split(",") if user.profile.address else []
    address_parts = [part.strip() for part in address_parts]

    country = address_parts[0] if len(address_parts) > 0 else ""
    city = address_parts[1] if len(address_parts) > 1 else ""

    match_priority = case(
        (shop_model.DeliveryPickUpPoint.city.ilike(f"%{city}%"), 1),
        (shop_model.DeliveryPickUpPoint.city.ilike(f"%{country}%"), 2),
        (shop_model.DeliveryPickUpPoint.address.ilike(f"%{city}%"), 3),
        (shop_model.DeliveryPickUpPoint.address.ilike(f"%{country}%"), 4),
        else_=5
    )

    pick_points = (
        db.query(shop_model.DeliveryPickUpPoint)
        .order_by(match_priority, shop_model.DeliveryPickUpPoint.created_at.desc())
        .all()
    )

    return pick_points


def create_meeting_point(db: Session, data: schemas.MeetingPoint):
    NewPoint = shop_model.DeliveryMeetingPoint(
        city=data.city,
        zipcode=data.zipcode,
        address=data.address
    )
    db.add(NewPoint)
    db.commit()
    return NewPoint


def get_meeting_points(db: Session):
    return db.query(shop_model.DeliveryMeetingPoint).filter(
        shop_model.DeliveryMeetingPoint.is_active == True
    ).all()
