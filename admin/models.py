from database import Base
from sqlalchemy import Boolean, Column, Enum, String
from sqlalchemy_utils import EmailType
from sqlalchemy.orm import relationship
from auth.schemas import AccountStatus


class Administrator(Base):
    __tablename__ = "administrator"

    id = Column(String(), primary_key=True, unique=True)
    fullname = Column(String(), default="")
    email_address = Column(EmailType(), default="", unique=True)
    password = Column(String())
    profile_pic = Column(String(), default="")
    account_status = Column(Enum(AccountStatus), default=AccountStatus.Enabled)

    forum_topics = relationship("ForumTopic", back_populates="admin", cascade="all,delete")

