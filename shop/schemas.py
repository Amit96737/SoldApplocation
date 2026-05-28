import json
from datetime import datetime
from pickle import FALSE
from database import SessionLocal
from pydantic import BaseModel, field_validator, Field, HttpUrl, root_validator
from typing import Optional, List
from enum import Enum
from profile.schemas import Profile
from auth.schemas import AccountStatus
import enum


class SaleStatus(str, Enum):
    Shipped = 'Shipped'
    NotShipped = 'NotShipped'
    Completed = 'Completed'


class ShoesSizeType(str, Enum):
    UK = "uk"
    US = "us"
    EU = "eu"


class ConditionTypeEnum(str, enum.Enum):
    NEW = "new"
    USED = "used"


class DeliveryMethodEnum(str, enum.Enum):
    PICKUP_POINT = "pick-up point"
    DOOR_TO_DOOR = "door-to-door"
    MEETING_POINT = "meeting point"


class ItemOwner(Profile):
    ratings_count: Optional[int] = 0
    average_rating: Optional[float] = 0.0
    account_status: Optional[AccountStatus] = AccountStatus.Enabled

    class Config:
        from_attributes = True


class ItemBase(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    images: Optional[List[str]] = []
    price: Optional[float] = 0
    size: Optional[str] = None
    state: Optional[str] = ""
    brand: Optional[str] = ""
    colors: Optional[List[str]] = []
    category: Optional[str] = ""
    sub_category: Optional[str] = ""
    type: Optional[str] = ""
    material: Optional[List[str]] = []
    condition: ConditionTypeEnum

    class Config:
        from_attributes = True


class AddItem(ItemBase):
    payment_methods: Optional[List[str]] = []
    shipping_methods: Optional[List[DeliveryMethodEnum]] = []
    hash_tags: Optional[List[str]] = []

    class Config:
        from_attributes = True

    # @field_validator('material')
    # def validate_material_length(cls, v):
    #     if v and len(v) > 3:
    #         raise ValueError("Maximum 3 materials are allowed.")
    #     return v


class UpdateItem(BaseModel):
    price: Optional[float] = 0
    images: Optional[List[str]] = []
    payment_methods: Optional[List[str]] = []
    shipping_methods: Optional[List[str]] = []


class ShopItemDetails(AddItem):
    id: str
    owner: Optional[ItemOwner] = None
    view_count: Optional[int] = 0
    interested_members: Optional[int] = 0
    is_sold: Optional[bool] = False
    date_created: datetime
    material: Optional[str] = ""
    shipping_methods: Optional[List[str]] = []

    class Config:
        from_attributes = True

    @field_validator('hash_tags', mode='before', check_fields=False)
    def parse_hash_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('shipping_methods', mode='before', check_fields=False)
    def parse_shipping_method(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('payment_methods', mode='before', check_fields=False)
    def parse_payment_methods(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('colors', mode='before', check_fields=False)
    def parse_colors(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('images', mode='before', check_fields=False)
    def parse_images(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    # @field_validator('material', mode='before', check_fields=False)
    # def parse_material(cls, v):
    #     if isinstance(v, str):
    #         try:
    #             return json.loads(v)
    #         except json.JSONDecodeError:
    #             raise ValueError("Invalid JSON string")
    #     return v


class ShopItem(ItemBase):
    id: Optional[str] = ""
    owner_id: Optional[str] = ""
    view_count: Optional[int] = 0
    is_sold: Optional[bool] = None
    date_created: Optional[datetime] = None
    hash_tags: Optional[List[str]] = []
    payment_methods: List[str] = []
    shipping_methods: Optional[List[str]] = []
    is_active: bool = True
    material: Optional[str] = ''
    is_boosted: bool = False

    class Config:
        from_attributes = True

    @field_validator('colors', mode='before', check_fields=False)
    def parse_colors(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('images', mode='before', check_fields=False)
    def parse_images(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('hash_tags', mode='before', check_fields=False)
    def parse_hash_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('payment_methods', mode='before', check_fields=False)
    def parse_payment_methods(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    @field_validator('shipping_methods', mode='before', check_fields=False)
    def parse_shipping_methods(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v

    # @field_validator('material', mode='before', check_fields=False)
    # def parse_material(cls, v):
    #     if isinstance(v, str):
    #         try:
    #             return json.loads(v)
    #         except json.JSONDecodeError:
    #             raise ValueError("Invalid JSON string")
    #     return v


class SellerWithItems(BaseModel):
    id: str
    fullname: str
    username: str
    address: str
    country: str
    profile_pic: HttpUrl
    # ratings_count: int
    # average_rating: float
    account_status: str
    items: List[ShopItem]

    class Config:
        from_attributes = True


class ShopBundleInDb(BaseModel):
    owner_id: str
    is_enabled: bool
    bundles: List[dict]


class ShopBundleUpdate(BaseModel):
    is_enabled: bool
    bundles: List[dict]


class BrandBase(BaseModel):
    name: str


class BrandInDb(BrandBase):
    id: str
    enabled: bool
    featured: bool
    date_created: str


class SizeInDb(BaseModel):
    id: str
    size: str
    date_created: datetime

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str
    translation_key: str


class CategoryInDb(CategoryBase):
    id: Optional[str] = None
    enabled: Optional[bool] = None
    featured: Optional[bool] = None
    priority: Optional[int] = None
    date_created: Optional[datetime] = datetime.now()

    class Config:
        from_attributes = True


class SubCategoryBase(BaseModel):
    name: Optional[str] = None
    translation_key: Optional[str] = None
    category_id: Optional[str] = None


class SubCategoryInDb(SubCategoryBase):
    id: Optional[str] = None
    parent_category_name: Optional[str] = None
    featured: Optional[bool] = None
    enabled: Optional[bool] = None

    class Config:
        from_attributes = True


class SubCategoryItemBase(BaseModel):
    name: str
    translation_key: str
    sub_category_id: str


class SubCategoryItemInDb(SubCategoryItemBase):
    id: str

    class Config:
        from_attributes = True


class BuyItem(BaseModel):
    item_id: List[str]
    delivery_method: DeliveryMethodEnum
    # payment_method: str
    delivery_details: Optional[str] = ""
    final_price: Optional[float] = 0


class SaleItemsInDb(BaseModel):
    id: str
    item_id: Optional[str] = ""
    item_image: Optional[str] = ""
    item_title: Optional[str] = ""
    item_brand: Optional[str] = ""
    item_subCategory: Optional[str] = ""
    delivery_method: Optional[str] = ""
    delivery_details: Optional[str] = ""
    payment_method: Optional[str] = ""
    final_price: Optional[float] = 0
    is_rated: Optional[bool] = True
    buyer_id: Optional[str] = ""
    seller_username: Optional[str] = ""
    buyer_username: Optional[str] = ""
    sale_status: SaleStatus
    date_created: datetime
    seller_id: Optional[str] = ""

    class Config:
        from_attributes = True


class RecentlyViewItemsSchema(BaseModel):
    id: str
    item: ShopItem
    view_at: datetime

    class Config:
        from_attributes = True


class ItemMaterialSchema(BaseModel):
    id: str
    name: str


class ShoeSizeSchema(BaseModel):
    id: str
    size: str


class ShoeSizeGroupedSchema(BaseModel):
    type: ShoesSizeType
    sizes: List[ShoeSizeSchema]



class RentalCreate(BaseModel):
    item_id: str
    start_date: datetime
    end_date: datetime


class RentalOut(BaseModel):
    id: str
    item_id: str
    renter_id: str
    start_date: datetime
    end_date: datetime
    returned_at: Optional[datetime]
    total_cost: Optional[float]
    is_active: bool

    class Config:
        orm_mode = True

class ReportReasonBase(BaseModel):
    title: str

class ReportReasonInDb(ReportReasonBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ItemReportCreate(BaseModel):
    item_id: str
    reason_ids: Optional[List[str]] = None
    other: Optional[str] = ""

class ItemReportInDb(BaseModel):
    id: str
    user_id: str
    item_id: str
    other: Optional[str] = ""
    created_at: datetime

    class Config:
        from_attributes = True

class ItemReportWithReasons(BaseModel):
    id: str
    user_id: str
    item_id: str
    other: Optional[str]
    created_at: datetime
    reasons: List[ReportReasonInDb]

    class Config:
        from_attributes = True


