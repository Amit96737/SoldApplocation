import json
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Optional, List
from shop.schemas import ShopItem
from profile.schemas import Profile
from auth.schemas import AccountStatus


class MessageType(str, Enum):
    Normal = 'Normal'
    Offer = 'Offer'


class ChatUser(Profile):
    online: Optional[bool] = False
    ratings_count: Optional[int] = 0
    average_rating: Optional[float] = 0.0
    account_status: Optional[AccountStatus] = AccountStatus.Enabled
    last_seen: Optional[datetime] = None

    @field_validator('country', mode='before', check_fields=False)
    def parse_json_string(cls, v):
        pass

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    message: Optional[str] = None
    offer_price: Optional[float] = 0.0
    item_id: Optional[str] = None
    item_price: Optional[float] = 0.0
    message_type: Optional[MessageType] = MessageType.Normal
    attachments: Optional[List[str]] = []


class SendMessage(MessageBase):
    receiver_id: str


class SendOffer(BaseModel):
    offer_price: Optional[float] = 0.0
    item_id: Optional[str] = None


class MessageInDb(MessageBase):
    id: str
    sender_id: str
    room_id: str
    created_at: datetime

    @field_validator('attachments', mode='before', check_fields=False)
    def parse_json_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    class Config:
        from_attributes = True


class GetRoomSchema(BaseModel):
    user_id: str
    item_id: Optional[str] = None


class ChatRoomInDb(BaseModel):
    id: Optional[str] = None
    last_message: Optional[str] = None
    user: Optional[ChatUser] = None
    item: Optional[ShopItem] = None
    unread_count: Optional[int] = None
    last_message_by: Optional[str] = None
    last_message_type: Optional[MessageType] = MessageType.Normal
    last_offer_price: Optional[float] = None
    last_item_price: Optional[float] = None
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True
