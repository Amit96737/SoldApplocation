import enum
from datetime import datetime
from sqlalchemy import Boolean, Column, Enum, String, DECIMAL, ForeignKey, Integer, DateTime, Text, Float
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy_utils import URLType


class AffiliateSlider(Base):
    __tablename__ = "affiliate_sliders"

    id = Column(String(), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    image = Column(URLType, default="")
    enabled = Column(Boolean(), default=True)
    redirect_path = Column(String(length=50), default="")


class Partner(Base):
    __tablename__ = "partner"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    logo = Column(URLType, nullable=True)
    description = Column(String)

    affiliate = relationship("Affiliate", back_populates="partner")


class Affiliate(Base):
    __tablename__ = "affiliate"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    partner_id = Column(String(36), ForeignKey("partner.id"), nullable=True)
    code = Column(String, unique=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    percentage = Column(Integer, default=10)
    max_uses = Column(Integer, default=10)
    use_count = Column(Integer, default=0)
    date_created = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="affiliate")
    subscriptions = relationship("UserSubscription", back_populates="affiliate")
    rewards = relationship("AffiliateReward", back_populates="affiliate")

    partner = relationship("Partner", back_populates="affiliate")


class AffiliateReward(Base):
    __tablename__ = "affiliate_rewards"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = Column(String, ForeignKey("users.id"), nullable=True)

    affiliate_id = Column(String, ForeignKey("affiliate.id"))
    subscription_id = Column(String, ForeignKey("user_subscription.id"))

    reward_type = Column(Enum("money", "package", name="reward_type_enum"))
    amount = Column(Float)
    status = Column(Enum("pending", "confirmed", "cancelled", name="reward_status_enum"))
    date_created = Column(DateTime, default=datetime.utcnow)
    confirm_date = Column(DateTime, nullable=True)

    referrer = relationship("User", back_populates="rewards")  # new user who subscribe with referral code
    affiliate = relationship("Affiliate", back_populates="rewards")
    subscriptions = relationship("UserSubscription", back_populates="rewards")  # new user who subscribe
