import datetime

from sqlalchemy import Column, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship

from database import Base


class UserRatings(Base):
    __tablename__ = 'user_ratings'
    id = Column(String, primary_key=True)
    value = Column(Float)
    review = Column(String)
    owner_id = Column(String, ForeignKey('users.id'))
    rated_user_id = Column(String, ForeignKey('users.id'))
    date_created = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", foreign_keys=rated_user_id, uselist=False)
    owner = relationship("User", foreign_keys=owner_id, uselist=False)

