from datetime import datetime, timezone

import pyotp, uuid
from sqlalchemy import Boolean, Column, Enum, String, DateTime, Table, ForeignKey, UniqueConstraint, Date
from sqlalchemy.orm import relationship
from sqlalchemy_utils import EmailType

from auth.schemas import AccountStatus
from auth.schemas import AuthProvider
from database import Base
from sqlalchemy.sql import func

# Association table for the many-to-many relationship between users and posts
user_favorite_topics = Table(
    'user_favorite_topics',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('forum_topic_id', String, ForeignKey('forum_topics.id'))
)

# Association table for the many-to-many relationship between users (followers and followings)
user_followings = Table(
    'user_followings',
    Base.metadata,
    Column('follower_id', String, ForeignKey('users.id'), primary_key=True),
    Column('following_id', String, ForeignKey('users.id'), primary_key=True)
)

# Association table for the many-to-many relationship between users (user and shop Item)
favourited_items = Table(
    'favourited_items',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('item_id', String, ForeignKey('shop_items.id')),
    Column('date_created', DateTime, default=datetime.now(timezone.utc), server_default=func.now())
)


class User(Base):
    __tablename__ = "users"

    id = Column(String(length=36), primary_key=True)
    email_address = Column(EmailType(), unique=True)
    phone_number = Column(String(length=100), default="")
    password = Column(String(length=300), default="")
    otp_secret = Column(String(length=32), default=pyotp.random_base32(length=32))
    account_status = Column(Enum(AccountStatus), default=AccountStatus.Enabled)
    auth_provider = Column(Enum(AuthProvider))
    is_email_verified = Column(Boolean(), default=False)
    is_number_verified = Column(Boolean(), default=False)
    is_seller = Column(Boolean, default=False, nullable=True)

    favourited_items = relationship('ShopItem', secondary=favourited_items, back_populates='favorited_by')

    # Users that this user is following
    following = relationship(
        'User',
        secondary=user_followings,
        primaryjoin=id == user_followings.c.follower_id,
        secondaryjoin=id == user_followings.c.following_id,
        backref='followed_by'
    )

    last_seen = Column(DateTime, default=datetime.now(timezone.utc))
    date_created = Column(DateTime, default=datetime.now(timezone.utc))

    favorited_topics = relationship('ForumTopic', secondary=user_favorite_topics, back_populates='favorited_by')

    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all,delete")

    preferences = relationship("Preference", uselist=False, cascade="all,delete")

    shop_items = relationship("ShopItem", back_populates="owner", cascade="all,delete")

    forum_topics = relationship("ForumTopic", back_populates="user", cascade="all,delete")

    shipping_info = relationship("ShippingInfo", uselist=False, back_populates="user", cascade="all,delete")

    payment_details = relationship("PaymentDetails", uselist=False, back_populates="user", cascade="all,delete")

    subscriptions = relationship("UserSubscription", back_populates="user")

    user_report_by = relationship("UserReport", back_populates="report_by", foreign_keys="[UserReport.report_by_id]")
    user_report_to = relationship("UserReport", back_populates="report_to", foreign_keys="[UserReport.report_to_id]")
    app_opens = relationship("AppOpen", back_populates="user", cascade="all, delete-orphan")
    affiliate = relationship("Affiliate", back_populates="user", uselist=False)
    rewards = relationship("AffiliateReward", back_populates="referrer")

    payment = relationship("Payment", uselist=False, back_populates="user", cascade="all,delete")
    payment_sale_item = relationship("ItemSalePayment", uselist=False, back_populates="user", cascade="all,delete")
    rentals = relationship("Rental", back_populates="renter")

    # allpayment = relationship("AllPayPayment", uselist=True, back_populates="user")


class AppOpen(Base):
    __tablename__ = "app_opens"

    id = Column(String(length=36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(length=36), ForeignKey("users.id"), nullable=False)
    opened_at = Column(DateTime, default=datetime.utcnow)
    opened_date = Column(Date, default=lambda: datetime.utcnow().date())

    __table_args__ = (UniqueConstraint('user_id', 'opened_date', name='uix_user_opened_date'),)

    user = relationship("User", back_populates="app_opens")
