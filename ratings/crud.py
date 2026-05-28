from uuid import uuid4

from fastapi import status
from sqlalchemy.orm import Session
from starlette.requests import Request

from I18n.load_language import get_lang_content
from auth import models as auth_model
from auth.models import User
from exception import UnicornException
from ratings import schemas, models
from shop import schemas as shop_schemas
from shop import models as shop_models


def rate_user(request: Request, data: schemas.RatingCreate, db: Session, user: User):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    if user.id != data.user_id:

        salesInDb = db.query(shop_models.Sales).filter_by(id=data.sale_id).first()
        salesInDb.is_rated = True

        userInDB = db.query(auth_model.User).filter(auth_model.User.id == data.user_id).first()
        unique_id = str(uuid4())

        if userInDB is None:
            raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                                   message=language_content.get('User not found'))

        ratingDb = models.UserRatings(
            id=unique_id,
            value=data.value,
            review=data.review,
            owner_id=user.id,
            rated_user_id=data.user_id
        )

        db.add(ratingDb)
        db.commit()
        db.refresh(ratingDb)

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('review submitted successfully'))
    else:
        raise UnicornException(status_code=status.HTTP_403_FORBIDDEN,
                               message=language_content.get('You can not rate yourself'))


def get_user_ratings(user_id: str, db: Session, user: User):
    userInDb = db.query(auth_model.User).filter(auth_model.User.id == user_id).first()

    if userInDb:
        ratingsInDb = db.query(models.UserRatings).filter(models.UserRatings.rated_user_id == user_id).all()
        return [
            schemas.RatingInDb(
                value=rating.value,
                review=rating.review,
                user_id=rating.owner_id,
                user_fullname=rating.owner.profile.fullname,
                user_profile_pic=rating.owner.profile.profile_pic,
                date_created=str(rating.date_created)
            ) for rating in ratingsInDb
        ]
    else:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="User with this id not found")
