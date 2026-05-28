from datetime import datetime

from sqlalchemy import Column, Text, Enum, ForeignKey, String, DateTime, Boolean, DECIMAL
from sqlalchemy.orm import relationship

from chats.schemas import MessageType
from database import Base


class ChatRoom(Base):
    __tablename__ = 'chat_rooms'

    id = Column(String(length=36), primary_key=True)
    users = Column(Text, default="[]")
    item_id = Column(String(length=36), ForeignKey('shop_items.id'), default=None)
    last_message = Column(Text, default="")
    last_message_by = Column(String(length=36), default="")
    last_message_type = Column(Enum(MessageType), default=MessageType.Normal)
    last_offer_price = Column(DECIMAL, default=0.0)
    last_item_price = Column(DECIMAL, default=0.0)
    last_message_at = Column(DateTime, default=datetime.utcnow())

    messages = relationship("Message", back_populates="chat_room")

    item = relationship("ShopItem", foreign_keys=item_id)


class Message(Base):
    __tablename__ = 'messages'

    id = Column(String(length=36), primary_key=True)
    room_id = Column(String(length=36), ForeignKey('chat_rooms.id'))
    sender_id = Column(String(length=36))
    offer_price = Column(DECIMAL(), default=0.0)
    item_price = Column(DECIMAL(), default=0.0)
    is_read = Column(Boolean(), default=False)
    message = Column(Text, default='')
    message_type = Column(Enum(MessageType), default=MessageType.Normal)
    attachments = Column(String(), default="[]")
    created_at = Column(DateTime(), default=datetime.utcnow())

    chat_room = relationship("ChatRoom", back_populates="messages")
