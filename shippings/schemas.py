from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ShippingEdit(BaseModel):
    address: Optional[str]
    city: Optional[str]
    zip_code: Optional[str]


class PickUpPoint(BaseModel):
    address: str
    city: Optional[str]
    zipcode: int

    class Config:
        from_attributes = True


class MeetingPoint(PickUpPoint):
    pass


class MeetingPointDetails(MeetingPoint):
    id: str

