import enum
from datetime import datetime

from decimal import Decimal
from sqlalchemy import Boolean, Column, Enum, String, DECIMAL, ForeignKey, Integer, DateTime, Text, Numeric, \
    Enum as SAEnum, Index
from sqlalchemy.orm import relationship
from database import Base
from auth.models import favourited_items
import uuid
from shop.schemas import SaleStatus, ShoesSizeType
from sqlalchemy import Enum as SQLEnum


class ItemMaterial(Base):
    __tablename__ = "shop_item_materials"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(length=255), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow)
    translation_key = Column(String(length=100), default="")


class ConditionTypeEnum(str, enum.Enum):
    NEW = "new"
    USED = "used"


class ShopItem(Base):
    __tablename__ = "shop_items"

    id = Column(String(length=36), unique=True, primary_key=True)
    owner_id = Column(String(length=36), ForeignKey("users.id"), default="")
    title = Column(String(length=200), default="")
    description = Column(Text, default="")
    images = Column(Text, default="[]")
    price = Column(DECIMAL(), default=0.0)
    colors = Column(Text, default="[]")
    brand = Column(String(length=200), default="")
    is_sold = Column(Boolean, default=False)
    size = Column(String(length=200), default="")
    state = Column(String(length=200), default="")
    category = Column(String(length=200), default="")
    sub_category = Column(String(length=200), default="")
    type = Column(String(length=200), default="")
    view_count = Column(Integer(), default=0)
    payment_methods = Column(Text, default="[]")
    shipping_methods = Column(Text, default="[]")
    hash_tags = Column(Text, default="[]")
    date_created = Column(DateTime, default=datetime.utcnow)
    material = Column(Text, default="")
    condition = Column(SQLEnum(ConditionTypeEnum), nullable=False)
    is_active = Column(Boolean, default=True)
    is_boosted = Column(Boolean, default=False)

    favorited_by = relationship('User', secondary=favourited_items, back_populates='favourited_items')

    owner = relationship("User", uselist=False, back_populates="shop_items")
    suggestions = relationship("SearchSuggestion", back_populates="item", cascade="all, delete-orphan")
    forum = relationship("ForumTopic", back_populates="item", cascade="all,delete")
    payment = relationship(
        "ItemSalePayment",
        back_populates="shop_item",
        uselist=False
    )
    rentals = relationship("Rental", back_populates="item")
    boosts = relationship("ItemBoost", back_populates="item")

class Bundles(Base):
    __tablename__ = "shop_bundles"

    owner_id = Column(String(), ForeignKey('users.id'), unique=True, primary_key=True)
    is_enabled = Column(Boolean, default=False)
    bundles = Column(String(), default="[{}]")
    user = relationship("User", uselist=False, foreign_keys=owner_id)


class Brands(Base):
    __tablename__ = "item_brands"

    id = Column(String(), unique=True, primary_key=True)
    name = Column(String(), default="", unique=True)
    enabled = Column(Boolean(), default=True)
    featured = Column(Boolean(), default=False)
    date_created = Column(DateTime, default=datetime.utcnow)


class Sizes(Base):
    __tablename__ = "item_sizes"

    id = Column(String(), unique=True, primary_key=True)
    size = Column(String(), default="")
    date_created = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(String(length=36), unique=True, primary_key=True)
    name = Column(String(length=200), default="", unique=True)
    translation_key = Column(String(length=100), default="")
    enabled = Column(Boolean, default=True)
    priority = Column(Integer(), default=0)
    featured = Column(Boolean, default=False)
    date_created = Column(DateTime, default=datetime.utcnow)

    sub_categories = relationship("SubCategory", back_populates="parent_category", cascade="all,delete")


class SubCategory(Base):
    __tablename__ = "sub_categories"

    id = Column(String(length=36), unique=True, primary_key=True)
    name = Column(String(length=200), default="")
    category_id = Column(String(length=36), ForeignKey("categories.id"), default="")
    translation_key = Column(String(length=100), default="")
    enabled = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)

    parent_category = relationship("Category", uselist=False, back_populates="sub_categories")
    category_items = relationship("SubCategoryItems", back_populates="sub_category", cascade="all,delete,delete-orphan")


class SubCategoryItems(Base):
    __tablename__ = "sub_categories_items"

    id = Column(String(length=36), unique=True, primary_key=True)
    name = Column(String(length=200), default="")
    sub_category_id = Column(String(length=36), ForeignKey("sub_categories.id"), default="")
    translation_key = Column(String(length=100), default="")

    sub_category = relationship("SubCategory", uselist=False, back_populates="category_items")
    sub_sub_category = relationship("SubSubCategoryItems", back_populates="sub_category",
                                    cascade="all,delete,delete-orphan")


class SubSubCategoryItems(Base):
    __tablename__ = "sub_sub_categories_items"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(length=200), nullable=False)
    translation_key = Column(String(length=100), default="")
    sub_category_id = Column(String(length=36), ForeignKey("sub_categories_items.id"))

    sub_category = relationship("SubCategoryItems", uselist=False, back_populates="sub_sub_category")
    sub_sub_category_level = relationship("SubSubCategoryItemsLevel", back_populates="sub_category_level",
                                          cascade="all,delete,delete-orphan")


class SubSubCategoryItemsLevel(Base):
    __tablename__ = "sub_sub_categories_items_level"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(length=200), nullable=False)
    translation_key = Column(String(length=100), default="")
    sub_category_id = Column(String(length=36), ForeignKey("sub_sub_categories_items.id"))

    sub_category_level = relationship("SubSubCategoryItems", uselist=False, back_populates="sub_sub_category_level")


class Colors(Base):
    __tablename__ = "colors"

    id = Column(String(length=36), unique=True, primary_key=True)
    color_name = Column(String(length=100), unique=True)
    translation_key = Column(String(length=200), default="")
    color_code = Column(String(length=50), default="")


class Sales(Base):
    __tablename__ = "shop_sales"

    id = Column(String(), unique=True, primary_key=True)
    item_id = Column(String(), ForeignKey('shop_items.id'))
    payment_id = Column(String(), ForeignKey('payment_sale_item.id'))
    table_payment_id = Column(String(), ForeignKey('payment_table.id'))
    delivery_method = Column(String(), default="")
    delivery_details = Column(String(), default="")

    is_protected_purchase = Column(Boolean, default=False)

    payment_method = Column(String(), default="paypal")
    final_price = Column(DECIMAL(), default=0)
    is_rated = Column(Boolean, default=False)
    sale_status = Column(Enum(SaleStatus), default=SaleStatus.NotShipped)
    buyer_id = Column(String(), ForeignKey('users.id'))
    date_created = Column(DateTime, default=datetime.utcnow)

    buyer = relationship("User", uselist=False, foreign_keys=buyer_id)

    shop_item = relationship("ShopItem", uselist=False, foreign_keys=item_id)
    payment = relationship("ItemSalePayment", uselist=False, back_populates="sale", foreign_keys=payment_id)

    allpaypayment = relationship("AllPayPayment", uselist=False, back_populates="sales", foreign_keys=table_payment_id)


class RecentlyViewItems(Base):
    __tablename__ = "recently_view_items"
    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = Column(String(), ForeignKey('shop_items.id'))
    user_id = Column(String(), ForeignKey('users.id'))
    view_at = Column(DateTime, default=datetime.utcnow())


class SearchSuggestion(Base):
    __tablename__ = "items_search_suggestion"
    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    term = Column(String, nullable=False)
    item_id = Column(String(length=36), ForeignKey("shop_items.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    item = relationship("ShopItem", back_populates="suggestions")


class DeliveryPickUpPoint(Base):
    __tablename__ = "delivery_pickup_points"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String(length=255))
    city = Column(String(length=155))
    zipcode = Column(Integer())
    created_at = Column(DateTime, default=datetime.utcnow)


class DeliveryMeetingPoint(Base):
    __tablename__ = "delivery_meeting_points"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String(length=255))
    city = Column(String(length=155))
    zipcode = Column(Integer())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ShoeSizes(Base):
    __tablename__ = "shoes_sizes"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    size = Column(String)
    type = Column(Enum(ShoesSizeType))


class Rental(Base):
    __tablename__ = "rentals"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to User who is renting
    renter_id = Column(String(length=36), ForeignKey("users.id"), nullable=False)

    # Foreign key to ShopItem being rented
    item_id = Column(String(length=36), ForeignKey("shop_items.id"), nullable=False)

    # Rental details
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    returned_at = Column(DateTime, nullable=True)

    total_cost = Column(DECIMAL(), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    renter = relationship("User", back_populates="rentals")
    item = relationship("ShopItem", back_populates="rentals")


def gen_uuid() -> str:
    return str(uuid.uuid4())


class BoostDuration(enum.Enum):
    DAYS_3 = 3
    DAYS_7 = 7


class ItemBoost(Base):
    __tablename__ = "item_boost"
    __table_args__ = (
        Index("ix_item_boost_shop_item_id", "shop_item_id"),
        Index("ix_item_boost_order_id", "order_id"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    shop_item_id = Column(String(36), ForeignKey("shop_items.id"), nullable=False)
    boost_duration = Column(SAEnum(BoostDuration), nullable=False)
    base_percent = Column(Numeric(5, 4), nullable=False)
    tax_percent = Column(Numeric(5, 4), nullable=False, default=Decimal("0.18"))
    final_percent_with_tax = Column(Numeric(6, 4), nullable=False)
    price = Column(Integer, nullable=False)
    start_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    order_id = Column(String(length=255), nullable=False)
    item = relationship("ShopItem", back_populates="boosts")
    is_active = Column(Boolean, default=False)
    payment_status = Column(String(20), nullable=False, default='pending')

class ItemReport(Base):
    __tablename__ = "item_report"
    id = Column(String(length=36), unique=True, primary_key=True)
    user_id = Column(String(), ForeignKey('users.id'))
    item_id = Column(String(length=36), ForeignKey("shop_items.id"))
    other = Column(Text, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ReportReason(Base):
    __tablename__ = "report_reasons"
    id = Column(String(length=36), unique=True, primary_key=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ItemReportReason(Base):
    __tablename__ = "item_report_reasons"
    id = Column(String(length=36), unique=True, primary_key=True)
    report_id = Column(String(36), ForeignKey("item_report.id"), nullable=False)
    reason_id = Column(String(36), ForeignKey("report_reasons.id"), nullable=False)

