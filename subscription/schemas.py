from pydantic import BaseModel, field_serializer, field_validator, Field
from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime
from subscription import models
import enum
from typing import List
from shop import models as shop_model


class SellerPlanOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    price: Decimal
    duration: Optional[int]
    subscription_type: str
    is_weekly: bool

    class Config:
        from_attributes = True


class verificationData(BaseModel):
    localVerificationData: str
    serverVerificationData: str
    source: str


class billingClientPurchase(BaseModel):
    originalJson: str
    signature: str


class PlatformEnum(str, enum.Enum):
    apple = "apple"
    google_play = "google_play"


class VerificationData(BaseModel):
    localVerificationData: Optional[Dict] = None
    serverVerificationData: Optional[str] = None
    source: PlatformEnum


class SubscribeSchema(BaseModel):
    SubscriptionType: models.SubscriptionTypeEnum
    AffiliateCode: Optional[str] = ""
    productId: str
    purchaseId: Optional[str] = None
    transactionDate: Optional[int] = None
    status: Optional[str] = None
    verificationData: Optional[VerificationData] = None
    autoRenewing: Optional[bool] = False
    expiresDate: Optional[int] = None
    originalTransactionId: Optional[str] = None


class SubscribeSchemaOut(BaseModel):
    id: str
    subscription_type: str
    subscribe_at: datetime
    expire_on: datetime
    platform : str
    product_id : str
    status: str
    auto_renewing: bool
    is_first_subscription: bool
    transaction_date: Optional[datetime] = None
    affiliate_id: Optional[str] = None

    class Config:
        from_attributes = True

    @field_serializer("subscribe_at", "expire_on", "transaction_date")
    def serialize_datetime(self, value: datetime) -> str:
        return value.strftime("%m/%d/%Y %I:%M:%S %p")


class BoostItemIn(BaseModel):
    item: List[str]
    day: shop_model.BoostDuration

    @field_validator('item')
    @classmethod
    def validate_item_list(cls, v):
        if len(v) < 1:
            raise ValueError('At least one item is required')
        return v

