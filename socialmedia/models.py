from datetime import datetime

from sqlalchemy import Boolean, Column, Enum, String, DECIMAL, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType

from database import Base


# class Status(Base):
#     __tablename__ = "statuses"
#
#     id = Column(UUIDType, ForeignKey("users.id"), primary_key=True)
#     user_id = Column(String(), default="")
#     status_url = Column(String(), default="")
#
#     date_created = Column(DateTime(timezone=True), default=datetime.now)
#
#     user = relationship("User", uselist=False, back_populates="statuses")
