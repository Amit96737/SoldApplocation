import uuid

from sqlalchemy import Column, String, Boolean, DECIMAL
from sqlalchemy_utils import URLType

from database import Base


class HomeSlider(Base):
    __tablename__ = "home_sliders"

    id = Column(String(), unique=True, primary_key=True)
    redirect_path = Column(String(length=50), default="")
    enabled = Column(Boolean(), default=True)
    slider_image_url = Column(URLType, default="")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(String(length=36), primary_key=True)
    name = Column(String(length=100), default="")
    icon = Column(URLType, default="")
    enabled = Column(Boolean, default=True)


class SupportedLanguage(Base):
    __tablename__ = "supported_languages"

    id = Column(String(length=36), primary_key=True)
    name = Column(String(length=100), default="English")
    code = Column(String(length=100), default="en")
    status = Column(Boolean, default=True)
    default = Column(Boolean, default=False)
    flag = Column(String(length=100), default="🇺🇸")



class ClubSoldDealsSlider(Base):
    __tablename__ = "club_deals_sliders"

    id = Column(String(), unique=True, primary_key=True)
    redirect_path = Column(String(length=50), default="")
    enabled = Column(Boolean(), default=True)
    slider_image_url = Column(URLType, default="")

