from pydantic import BaseModel
from typing import Optional
from pydantic import BaseModel
from enum import Enum as PyEnum


class SubscriptionPaymentRequest(BaseModel):
    plan_id: str


class PaymentRequest(BaseModel):
    price: float
    description: Optional[str] = "Description not provided"
    shop_item_id: str

class PaymentStatusUpdate(BaseModel):
    order_id: str

class PaymentStatus(PyEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
