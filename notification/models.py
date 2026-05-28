from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Enum, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from notification.schemas import NotificationType, NotificationAction


class Notifications(Base):
    __tablename__ = "notifications"

    id = Column(String(length=36), primary_key=True, unique=True)
    receiver_id = Column(String(length=36))
    sender_id = Column(String(length=36), ForeignKey('users.id'), nullable=True)
    item_id = Column(String(length=36), default="")
    sale_id = Column(String(length=36), default="")
    type = Column(Enum(NotificationType), default=NotificationType.Normal)
    notification_action = Column(Enum(NotificationAction), default=None)
    date_created = Column(DateTime(), default=datetime.now(timezone.utc))
    is_read = Column(Boolean, default=False)
    data = Column(String, default="")

    sender = relationship("User", foreign_keys=sender_id, uselist=False)


