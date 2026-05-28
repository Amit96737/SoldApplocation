from sqlalchemy import Column, Enum, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utils import URLType, UUIDType, CountryType
from datetime import datetime
from sqlalchemy import DateTime

from database import Base
from profile.schemas import Sex


class Profile(Base):
    __tablename__ = "profile"

    id = Column(String(length=36),  ForeignKey("users.id"), primary_key=True, unique=True)
    fullname = Column(String(length=50), default="")
    about = Column(String(length=200), default="")
    username = Column(String(length=100), default="")
    profile_pic = Column(URLType, default="")
    country = Column(CountryType, default="")
    sex = Column(Enum(Sex), default=Sex.Undisclosed)
    address = Column(String(length=200), default="")
    nickname = Column(String(length=255), default="")
    company_name = Column(String(length=100), default="", nullable=True)
    company_registration_num = Column(String(length=100), default="", nullable=True)

    user = relationship("User", uselist=False, back_populates="profile", cascade="all,delete")

