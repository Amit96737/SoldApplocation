import uuid
from typing import Optional

from sqlalchemy.orm import Session

from preferences import schemas, models


def update_user_pref(user_id: str, db: Session, pref_data: Optional[schemas.Preferences] = None):
    pass


async def set_up_user_pref(user_id: uuid, db: Session):
    userPrefModel = models.Preference(user_id=user_id)
    db.add(userPrefModel)
    db.commit()
    db.refresh(userPrefModel)

    return userPrefModel
