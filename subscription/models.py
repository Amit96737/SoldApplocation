import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum
from sqlalchemy import Enum as SQLEnum


class SubscriptionTypeEnum(str, enum.Enum):
    SELLER = "seller"
    FEATURED_DRESSING = "featured-dressing"
    TRENDING_SEARCH = "trending-search"
    BOOSTED_VISIBILITY = "boosted-visibility"
    RENTAL = 'rental'


class UserSubscription(Base):
    __tablename__ = "user_subscription"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    subscribe_at = Column(DateTime, default=datetime.utcnow)
    expire_on = Column(DateTime, nullable=True)

    affiliate_id = Column(String(36), ForeignKey("affiliate.id"), nullable=True)
    is_first_subscription = Column(Boolean, default=True)
    subscription_type = Column(SQLEnum(SubscriptionTypeEnum))

    platform = Column(String)
    product_id = Column(String)
    status = Column(String)
    auto_renewing = Column(Boolean, default=False)
    transaction_date = Column(DateTime, nullable=True)

    body = Column(JSON, nullable=True)

    # relations
    user = relationship("User", back_populates="subscriptions")
    affiliate = relationship("Affiliate", back_populates="subscriptions")
    rewards = relationship("AffiliateReward", back_populates="subscriptions")
