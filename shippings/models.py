from datetime import datetime

import pyotp
from sqlalchemy import Boolean, Column, Enum, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class ShippingInfo(Base):
    __tablename__ = "shipping_info"

    id = Column(String(length=36), unique=True, primary_key=True)
    user_id = Column(String(length=36), ForeignKey("users.id"))
    address = Column(String(length=200), default="")
    city = Column(String(length=200), default="")
    zip_code = Column(String(length=200), default="")

    user = relationship("User", uselist=False, back_populates="shipping_info")
