import json
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, field_validator


class ForumTopicCategory(str, Enum):
    Clothes = 'Clothes'
    Shoes = 'Shoes'
    Advice = 'Advice'
    Accessories = 'Accessories'


class AddTopic(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    images: Optional[List[str]] = []
    category: Optional[ForumTopicCategory] = ForumTopicCategory.Clothes
    item_id: Optional[str] = None


class TopicInDb(AddTopic):
    id: str
    user_username: Optional[str] = ""
    user_id: Optional[str] = ""
    user_fullname: Optional[str] = ""
    user_profile_pic: Optional[str] = ""
    comment_count: Optional[int] = 0
    date_created: datetime

    @property
    def profile_picture(self):
        userFullName = self.user_fullname.replace(" ", "+") if self.user_username else "User"
        return self.user_profile_pic or f"https://eu.ui-avatars.com/api/?name={userFullName}&size=250"

    @field_validator('images', mode='before', check_fields=False)
    def parse_images_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    class Config:
        from_attributes = True


class AddTopicAnswer(BaseModel):
    answer: str
    attachment: Optional[List[str]] = []
    topic_id: str


class TopicAnswerInDb(AddTopicAnswer):
    id: Optional[str] = ""
    user_username: Optional[str] = ""
    user_id: Optional[str] = ""
    user_fullname: Optional[str] = ""
    user_profile_pic: Optional[str] = ""
    date_answered: datetime

    @property
    def profile_picture(self):
        userFullName = self.user_fullname.replace(" ", "+") if self.user_username else "User"
        return self.user_profile_pic or f"https://eu.ui-avatars.com/api/?name={userFullName}&size=250"

    @field_validator('images', mode='before', check_fields=False)
    def parse_images_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('attachment', mode='before', check_fields=False)
    def ignore_attachment(cls, v):
        return json.loads(v)

    class Config:
        from_attributes = True
