from typing import Optional
from pydantic import BaseModel

from auth.schemas import AccountStatus
from shop import schemas as shop_schema


class AdminCreate(BaseModel):
    email_address: Optional[str] = "admin@gmail.com"
    password: Optional[str] = "admin"
    fullname: Optional[str] = "Administrator"


class AdminInDb(BaseModel):
    id: Optional[str] = None
    email_address: Optional[str] = "user@gmail.com"
    fullname: Optional[str] = None
    profile_pic: Optional[str] = None
    account_status: Optional[AccountStatus] = None

    @property
    def profile_picture(self):
        userFullName = self.fullname.replace(" ", "+") if self.fullname else "User"
        return self.profile_pic or f"https://eu.ui-avatars.com/api/?name={userFullName}&size=250"

    class Config:
        from_attributes = True


class CreateShoesSize(BaseModel):
    size: str
    type: shop_schema.ShoesSizeType
