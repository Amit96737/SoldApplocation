import datetime
from typing import Optional

from pydantic import BaseModel


class RatingCreate(BaseModel):
    value: float
    review: str
    sale_id: Optional[str] = ""
    user_id: str


class RatingInDb(RatingCreate):
    user_fullname: str
    user_profile_pic: str
    date_created: Optional[str] = str
