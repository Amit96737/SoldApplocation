from pydantic import BaseModel
from enum import Enum as PyEnum

class PaymentStatusUpdate(BaseModel):
    order_id: str

class AllPayPaymentStatus(str, PyEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"