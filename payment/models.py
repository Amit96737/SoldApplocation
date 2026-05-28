from sqlalchemy import Boolean, Column, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
import uuid, enum
from sqlalchemy.dialects.postgresql import JSONB, JSON
from datetime import datetime
from sqlalchemy import Enum
from payment.schemas import AllPayPaymentStatus




class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class PaymentDetails(Base):
    __tablename__ = "payment_details"

    id = Column(String(), primary_key=True)
    account_name = Column(String(), default="")
    paypal_url = Column(String(), default="")
    user_id = Column(String(), ForeignKey("users.id"))

    user = relationship("User", uselist=False, back_populates="payment_details")


class Payment(Base):
    __tablename__ = "payment"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(), ForeignKey("users.id"))
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)

    date_created = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    succeed_at = Column(DateTime, nullable=True)

    request_body = Column(JSONB)
    response_body = Column(JSONB, nullable=True)
    paypal_pay_id = Column(String, nullable=False, unique=True)
    paypal_payer_email = Column(String, nullable=True)
    paypal_event_id = Column(String, nullable=True)  # or order id
    payment_method = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    payer_info = Column(JSONB, nullable=True)

    decline_reason = Column(String, nullable=True)
    user = relationship("User", uselist=False, back_populates="payment")


class ItemSalePayment(Base):
    __tablename__ = "payment_sale_item"

    id = Column(String(length=36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = Column(String(), ForeignKey('shop_items.id'))
    user_id = Column(String(), ForeignKey("users.id"))  # payer
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)

    date_created = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    succeed_at = Column(DateTime, nullable=True)

    request_body = Column(JSONB)  # buy item user request
    response_body = Column(JSONB, nullable=True)  # paypal
    paypal_pay_id = Column(String, nullable=False, unique=True)
    paypal_payer_email = Column(String, nullable=True)
    paypal_event_id = Column(String, nullable=True)  # or order id
    payment_method = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    payer_info = Column(JSONB, nullable=True)

    decline_reason = Column(String, nullable=True)

    shop_item = relationship("ShopItem", uselist=False, back_populates="payment", foreign_keys=item_id)
    sale = relationship(
        "Sales",
        back_populates="payment",
        uselist=False
    )
    user = relationship("User", uselist=False, back_populates="payment_sale_item", foreign_keys=user_id)


class AllPayPayment(Base):
    __tablename__ = "payment_table"
    id = Column(String(), primary_key=True)
    payment_url = Column(String(), default="")
    order_id = Column(String, index=True, unique=True)
    status = Column(
        Enum(AllPayPaymentStatus, name="payment_status_enum", native_enum=True),
        default=AllPayPaymentStatus.PENDING
    )
    user_id = Column(String(), ForeignKey("users.id"))
    date_created = Column(DateTime, default=datetime.now, nullable=False)
    sales = relationship("Sales", back_populates="allpaypayment", foreign_keys="[Sales.table_payment_id]")
    user = relationship("User")

    webhook_payload = Column(JSON, nullable=True)