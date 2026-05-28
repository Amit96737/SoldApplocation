import json
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette import status

from auth.models import User
from exception import UnicornException
from shop import models as shop_models
from shop import schemas as shop_schemas
from socialmedia import schemas, models
import operator


def post_status(status_data: schemas.PostStatus, db: Session, current_user: User):
    unique_id = str(uuid4())

    statusModel = models.Status(
        id=unique_id,
        user_id=current_user.id,
        status_url=status_data.status_url
    )

    db.add(statusModel)
    db.commit()
    db.refresh(statusModel)

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message="Status uploaded successfully")


def get_status(user_id: str, db: Session, current_user: User):
    statusInDb = db.query(models.Status).filter(models.Status.user_id == user_id).all()

    userStatusList = [
        schemas.StatusInDb(
            status_url=userStatus.status_url,
            full_name=userStatus.user.profile.full_name,
            user_profile_pic=userStatus.user.profile.profile_pic
        ) for userStatus in statusInDb
    ]

    userStatusList.reverse()

    return userStatusList

