from datetime import datetime

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class NotificationType(str, Enum):
    Normal = 'normal'
    ItemSale = 'itemSale'
    ItemShipped = 'itemShipped'
    ItemSaleCompleted = 'itemSaleCompleted'
    Welcome = 'welcome'
    NewMessage = 'newMessage'
    NewOffer = 'newOffer'
    Affiliate = "affiliate"
#   add new
    requestResponse = 'requestResponse'
    expiringSubscriptions = 'expiringSubscriptions'
    unsoldItems = 'unsoldItems'
    saleNotification = 'saleNotification'

class NotificationAction(str, Enum):
    CompleteBooking = 'completeBooking'
    RejectBooking = 'rejectBooking'


class NotificationBase(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    receiver_id: Optional[str] = None
    type: Optional[NotificationType] = NotificationType.Normal
    notification_action: Optional[NotificationAction] = None
    item_id: Optional[str] = ""
    chat_id: Optional[str] = ""
    sale_id: Optional[str] = ""


class NotificationInDb(NotificationBase):
    id: str
    sender_id: Optional[str] = ""
    sender_fullname: Optional[str] = ""
    sender_profile_pic: Optional[str] = ""
    date_created: datetime
    is_read: bool

    @property
    def profile_picture(self):
        userFullName = self.sender_fullname.replace(" ", "+") if self.sender_fullname else "User"
        return self.sender_profile_pic or f"https://eu.ui-avatars.com/api/?name={userFullName}&size=250"

    class Config:
        from_attributes = True
