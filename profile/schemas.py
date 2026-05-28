import json
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict,Any

from pydantic import BaseModel, field_validator, Field

from auth.schemas import AuthProvider, AccountStatus


class Sex(str, Enum):
    Male = 'Male'
    Female = 'Female'
    Undisclosed = 'Undisclosed'


class Profile(BaseModel):
    id: Optional[str] = ""
    fullname: Optional[str] = ""
    address: Optional[str] = ""
    username: Optional[str] = ""
    country: Optional[str] = None
    profile_pic: Optional[str] = ""
    nickname: Optional[str] = ""
    company_name: Optional[str] = None
    company_registration_num: Optional[str] = None

    @property
    def profile_picture(self):
        userFullName = self.fullname.replace(" ", "+") if self.fullname else "User"
        return self.profile_pic or f"https://eu.ui-avatars.com/api/?name={userFullName}&size=250"

    # @property
    # def fullname(self):
    #     return self.fullname

    class Config:
        from_attributes = True


class ProfileEdit(Profile):
    phone_number: Optional[str] = None
    about: Optional[str] = None
    sex: Optional[Sex] = Sex.Undisclosed
    show_location: Optional[bool] = True
    show_notification: Optional[bool] = True
    holiday_mode: Optional[bool] = True
    company_name: Optional[str] = None
    company_registration_num: Optional[str] = None


class ProfileInDb(Profile):
    nickname: Optional[str] = ""
    email_address: Optional[str] = ""
    phone_number: Optional[str] = ""
    about: Optional[str] = ""
    sex: Optional[Sex] = Sex.Undisclosed
    show_location: Optional[bool] = None
    show_notification: Optional[bool] = None
    is_number_verified: Optional[bool] = None
    is_email_verified: Optional[bool] = None
    holiday_mode: Optional[bool] = None
    followers: Optional[List[str]] = []
    online: Optional[bool] = False
    ratings_count: Optional[int] = 0
    average_rating: Optional[float] = 0.0
    last_seen: Optional[datetime] = None
    following: Optional[List[str]] = []
    favorited_topics: Optional[List[str]] = []
    favorite_items: Optional[List[str]] = []
    items_count: Optional[int] = 0
    auth_provider: Optional[AuthProvider] = None
    date_created: Optional[datetime] = None
    account_status: Optional[AccountStatus] = None
    is_seller: Optional[bool] = False
    company_name: Optional[str] = None
    company_registration_num: Optional[str] = None
    subscriptions: Optional[Any] = None

    @property
    def profile_picture(self):
        userFullName = self.fullname.replace(" ", "+") if self.fullname else "User"
        return self.profile_pic or f"https://eu.ui-avatars.com/api/?name={userFullName}&size=250"

    @field_validator('followers', mode='before', check_fields=False)
    def parse_followers_string(cls, v):
        pass

    @field_validator('following', mode='before', check_fields=False)
    def parse_following_string(cls, v):
        pass

    @field_validator('favorite_items', mode='before', check_fields=False)
    def parse_json_string(cls, v):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string")

    @field_validator('favorited_topics', mode='before', check_fields=False)
    def ignore_favorited_topics(cls, v):
        pass

    class Config:
        from_attributes = True
