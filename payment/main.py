from fastapi import Depends, APIRouter, Header
from sqlalchemy.orm import Session
from starlette.requests import Request

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from payment import crud, schema
from starlette.background import BackgroundTasks

from payment.crud import payment_webhook

router = APIRouter(
    prefix="/payment",
    tags=['Payment']
)

@router.get("/{user_id}/details", tags=["Payment"])
async def get_payment_details(user_id: str, current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    return crud.get_payment_details(user_id, db)


@router.put("/details", tags=["Payment"])
async def update_payment_details(request: Request, payment_details_data: dict = {"paypal_url": "String"},
                                 current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    paypalUrl = payment_details_data.get('paypal_url')
    user = await crud.update_payment_details(request, paypalUrl, current_user, db)
    return user


# @router.post(path="/create-subscription-payment")
# async def create_subscription_payment(
#         data: schema.SubscriptionPaymentRequest,
#         db: Session = Depends(get_db)
# ):
#     return crud.paypal_create_payment_session(data, db=db)


@router.get(path="/verify-payment")
async def verify_payment(token: str, PayerID: str):
    return crud.verify_payments(order_id=token)

@router.post(path="/webhook")
async def paypal_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    data = await request.json()
    return crud.handler_paypal_webhook(data, db, background_tasks=background_tasks)


@router.post("/payment-webhook", tags=["Payment"])
async def payment_success(background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return payment_webhook(background_tasks=background_tasks, data=data,db=db, request=request)

