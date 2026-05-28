from database import Base
import uuid
from sqlalchemy import Column, ForeignKey, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime


class UserReport(Base):
    __tablename__ = "user_report"
    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_by_id = Column(String(length=36), ForeignKey("users.id"), nullable=False)
    report_to_id = Column(String(length=36), ForeignKey("users.id"), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    reason = Column(String(length=255), nullable=False)
    description = Column(Text, nullable=False)

    # relation
    report_by = relationship("User", back_populates="user_report_by", foreign_keys=[report_by_id])
    report_to = relationship("User", back_populates="user_report_to", foreign_keys=[report_to_id])

