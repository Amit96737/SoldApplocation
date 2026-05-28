from sqlalchemy import Boolean, Column, String, ForeignKey

from database import Base


class Preference(Base):
    __tablename__ = "preferences"

    user_id = Column(String(length=36), ForeignKey("users.id"), primary_key=True)
    show_location = Column(Boolean(), default=True)
    show_notification = Column(Boolean(), default=True)
    holiday_mode = Column(Boolean(), default=False)
