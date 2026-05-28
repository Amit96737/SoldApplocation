from uuid import uuid4
import random
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request
from I18n.load_language import get_lang_content
from auth.models import User
from exception import UnicornException
from payment import models, schema
from fastapi import HTTPException
import requests
from requests.auth import HTTPBasicAuth
from constants import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_ENV
from subscription import models as subscription_mode, crud as subscription_crud
import logging
from datetime import datetime
from shop import crud as shop_crud, models as shop_models

from payment.models import AllPayPayment
from shop.models import ShopItem
from starlette.background import BackgroundTasks
import hashlib
import uuid
import requests
from typing import Dict, Any
from payment.schemas import AllPayPaymentStatus
from shop.schemas import SaleStatus
import hmac
from fastapi.responses import RedirectResponse
from constants import ALL_PAY_LOGIN_KEY, ALL_PAY_API_KEY, ALL_PAY_PAYMENT_API_URL

from shop.models import Sales
from notification import schemas as notification_schemas
from notification import crud as notification_crud


async def update_payment_details(request: Request, paypal_url: str, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    paypal_username = await get_paypal_username(language_content, paypal_url)

    if paypal_username:
        paymentDetailsInDb = db.query(models.PaymentDetails).filter(
            models.PaymentDetails.user_id == current_user.id).first()

        if paymentDetailsInDb:
            paymentDetailsInDb.paypal_url = paypal_url
            paymentDetailsInDb.account_name = paypal_username

            db.commit()

            paymentDetailsInDb = db.query(models.PaymentDetails).filter(
                models.PaymentDetails.user_id == current_user.id).first()

            return {"message": language_content.get('payment details updated successfully'),
                    "data": paymentDetailsInDb,
                    "status": True}

        else:
            unique_id = str(uuid4())
            paymentDetailsModel = models.PaymentDetails(
                id=unique_id,
                account_name=paypal_username,
                paypal_url=paypal_url,
                user_id=current_user.id
            )

            db.add(paymentDetailsModel)
            db.commit()
            db.refresh(paymentDetailsModel)

            return {"message": language_content.get('payment details updated successfully'),
                    "data": paymentDetailsInDb,
                    "status": True}


def get_payment_details(user_id: User, db: Session):
    paymentDetailsInDb = db.query(models.PaymentDetails).filter(
        models.PaymentDetails.user_id == user_id).first()

    if paymentDetailsInDb:
        return {"message": "Payment details gotten successfully", "data": paymentDetailsInDb}
    else:
        raise UnicornException(status_code=status.HTTP_200_OK,
                               message="No payment details found for this user")


def user_payment_details(user_id, db: Session):  # this is for home api or screen
    paymentDetailsInDb = db.query(models.PaymentDetails).filter(
        models.PaymentDetails.user_id == user_id).first()
    if not paymentDetailsInDb:
        return None
    return paymentDetailsInDb


async def get_paypal_username(language_content: dict, url: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract the Twitter title meta tag from PayPal website
            paypal_twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
            paypal_title = paypal_twitter_title['content'].strip() if paypal_twitter_title else 'No Twitter title found'

            if paypal_title.split()[0] != "Pay":
                raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                                       message=language_content.get('we cant find this paypal profile"'))

            else:

                twitter_title_split = paypal_title.split()
                twitter_title_split.remove("Pay")
                twitter_title_split.remove("using")
                twitter_title_split.remove("PayPal.Me")

                paypal_user_name = " ".join(twitter_title_split)

                return paypal_user_name

    except httpx.RequestError as e:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('enter a valid paypal me url'))

    except Exception:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('enter a valid paypal me url'))


PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com" if PAYPAL_ENV == "sandbox" else "https://api-m.paypal.com"


def get_paypal_access_token():
    url = PAYPAL_BASE_URL + "/v1/oauth2/token"
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}
    response = requests.post(url, headers=headers, data=data,
                             auth=HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET))
    return response.json()['access_token']


# def create_payment_request(db: Session, response: dict, current_user, data: schema.PaymentRequest):
#     print(response)
#     print(response['id'])
#
#     payment = models.Payment(
#         request_body=response,
#         paypal_pay_id=response['id'],
#         intent=response['intent'],
#         subscription_plan_id=data.subscription_plan_id,
#         user_id=current_user.id
#     )
#
#     db.add(payment)
#     db.commit()


def create_payment_request(db: Session, response: dict, current_user, data: schema.PaymentRequest, sale_data):
    order_id = response.get('id')
    intent = response.get('intent', 'CAPTURE')

    payment = models.ItemSalePayment(
        request_body=sale_data,
        paypal_pay_id=order_id,  # order_id used as main reference in V2
        intent=intent,
        item_id=data.shop_item_id,
        user_id=current_user.id,
        status=models.PaymentStatus.pending  # optionally set initial status
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)


def paypal_create_payment_session(data: schema.PaymentRequest, db: Session, current_user, sale_data):
    access_token = get_paypal_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "ILS",
                "value": f"{data.price}"
            },
            "description": data.description,
            "custom_id": "Sold App"
        }],
        "application_context": {
            "return_url": "sold://payment-success",
            "cancel_url": "sold://payment-cancelled"
        }
    }

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/checkout/orders",
        headers=headers,
        json=order_payload
    )
    response_data = response.json()

    create_payment_request(
        db=db,
        response=response_data,
        current_user=current_user,
        data=data,
        sale_data=sale_data
    )
    return HTTPException(status_code=200, detail=response_data)


# def verify_payments(paymentId: str, PayerID: str):
#     access_token = get_paypal_access_token()
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {access_token}"
#     }
#     execute_data = {
#         "payer_id": PayerID
#     }
#     response = requests.post(f"https://api-m.sandbox.paypal.com/v1/payments/payment/{paymentId}/execute",
#                              headers=headers, json=execute_data)
#
#     return response.json()


def verify_payments(order_id: str):
    access_token = get_paypal_access_token()  # Your token generation function
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers=headers
    )

    if response.status_code != 201:
        raise Exception(f"Payment capture failed: {response.status_code} - {response.text}")

    return response.json()


def handler_paypal_webhook(data, db: Session, background_tasks):
    event_type = data.get("event_type")
    resource = data.get("resource")
    capture_id = resource.get("id")

    logging.info(f"Webhook Event: {event_type}, Resource ID: {capture_id}")

    # V2 uses 'resource.supplementary_data.related_ids.order_id' or just capture ID
    parent_payment = (
            resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id") or
            resource.get("id")
    )

    payment_obj = db.query(models.ItemSalePayment).filter(
        models.ItemSalePayment.paypal_pay_id == parent_payment).first()

    if not payment_obj:
        logging.error(f"Payment ID not found: {parent_payment}")
        return UnicornException(status_code=404, message=f"{parent_payment} not found")

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        amount = resource.get("amount", {}).get("value")
        payment_obj.amount = amount
        payment_obj.status = models.PaymentStatus.succeeded
        payment_obj.response_body = data
        payment_obj.payment_method = resource.get("payment_source", {}).get("type", "")
        payment_obj.succeed_at = datetime.utcnow()

        shop_crud.create_buy_item(
            background_tasks=background_tasks,
            sale_data=payment_obj.request_body,
            user=payment_obj.user,
            db=db
        )


    elif event_type == "PAYMENT.CAPTURE.DENIED":
        reason = resource.get("status_details", {}).get("reason")
        # print(f"Payment denied: {capture_id}, Reason: {reason}")
        payment_obj.status = models.PaymentStatus.failed
        payment_obj.response_body = data

    elif event_type == "CHECKOUT.ORDER.APPROVED":
        payer_info = resource.get("payer", {})
        payment_obj.payer_info = payer_info
        payment_obj.intent = "CAPTURE"
        payment_obj.paypal_payer_email = payer_info.get("email_address", "")

        amount = resource.get("amount", {}).get("value")
        payment_obj.amount = amount
        payment_obj.status = models.PaymentStatus.succeeded
        payment_obj.response_body = data
        payment_obj.payment_method = resource.get("payment_source", {}).get("type", "")
        payment_obj.succeed_at = datetime.utcnow()

        shop_crud.create_buy_item(
            background_tasks=background_tasks,
            sale_data=payment_obj.request_body,
            user=payment_obj.user,
            db=db
        )

    else:
        logging.debug(f"Unhandled event type: {event_type}")

    db.commit()
    db.refresh(payment_obj)

    return UnicornException(status_code=200, message="Webhook received successfully.")


def create_payment_details(db: Session, data: dict, user_id: str, payment_url: str, order_id: str):
    payment = AllPayPayment(
        id=str(uuid.uuid4()),
        order_id=order_id,
        user_id=user_id,
        payment_url=payment_url,
        status=AllPayPaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_api_signature(params: Dict[str, Any], api_key: str) -> str:
    sorted_params = dict(sorted(params.items()))
    chunks = []

    for key, value in sorted_params.items():
        if key == "sign":
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    sorted_item = dict(sorted(item.items()))
                    for inner_key, inner_value in sorted_item.items():
                        if isinstance(inner_value, float):
                            val = ('%.2f' % inner_value).rstrip('0').rstrip('.')
                        else:
                            val = str(inner_value)
                        if val.strip() != "":
                            chunks.append(val)
                else:
                    if isinstance(item, float):
                        val = ('%.2f' % item).rstrip('0').rstrip('.')
                    else:
                        val = str(item)
                    if val.strip() != "":
                        chunks.append(val)
        else:
            if isinstance(value, float):
                val = ('%.2f' % value).rstrip('0').rstrip('.')
            else:
                val = str(value)
            if val.strip() != "":
                chunks.append(val)

    signature_string = ":".join(chunks) + ":" + api_key
    signature = hashlib.sha256(signature_string.encode("utf-8")).hexdigest()
    return signature


def get_payment_url(user: User, shop_items_ids: list[str], db: Session, final_price: float = 0.0) -> Dict[str, Any]:
    order_id = ''.join(str(d) for d in random.sample(range(10), 8))
    items_in_db = db.query(ShopItem).filter(ShopItem.id.in_(shop_items_ids)).all()

    items_payload = [
        {
            "name": item.title,
            "price": float(final_price),
            "qty": "1"
        } for item in items_in_db
    ]
    payload = {
        "login": ALL_PAY_LOGIN_KEY,
        "order_id": order_id,
        "amount": float(final_price),
        "currency": "ILS",
        "client_name": user.email_address.split('@')[0],
        "client_email": user.email_address,
        "items": items_payload,
        "success_url": f"https://sold.csdevhub.com/api/v1/shop/item/buy/payment-success?item_id={shop_items_ids[0]}",
        "fail_url": f"https://sold.csdevhub.com/api/v1/shop/item/buy/payment-failed?item_id={shop_items_ids[0]}"
    }

    payload["sign"] = get_api_signature(payload, ALL_PAY_API_KEY)

    try:
        response = requests.post(ALL_PAY_PAYMENT_API_URL, json=payload)
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

    apppay_url = data.get("payment_url")
    if not apppay_url:
        raise HTTPException(status_code=400, detail="Payment URL not Found")

    create_payment_details(db, {"item_id": shop_items_ids}, user.id, apppay_url, order_id)
    data["order_id"] = order_id
    return data


def payment_webhook(background_tasks: BackgroundTasks, request: Request, data: dict, db: Session):
    status_map = {0, 1}
    payload_status = data.get("status")
    client_email = data.get("client_email")

    if payload_status not in status_map:
        raise HTTPException(status_code=400, detail="Unknown status found")

    payment = db.query(AllPayPayment).join(User).filter(
        User.email_address == client_email,
        AllPayPayment.status == AllPayPaymentStatus.PENDING
    ).order_by(AllPayPayment.id.desc()).first()

    payment.webhook_payload = data

    sales = db.query(Sales).filter(Sales.table_payment_id == payment.id).all()
    if payload_status == 1:
        payment.status = AllPayPaymentStatus.SUCCESS
        for sale in sales:
            sale.sale_status = "Shipped"
            sale.shop_item.is_sold = True
        db.commit()

        # use is_protected_purchase
        # for sale in sales:
        #     sale.shop_item.is_sold = True
        #     if sale.is_protected_purchase:
        #         sale.sale_status = SaleStatus.NotShipped
        #     else:
        #         sale.sale_status = SaleStatus.Shipped
        # db.commit()

        for sale in sales:
            seller_id = sale.shop_item.owner_id

            notification_schema = notification_schemas.NotificationBase(
                receiver_id=seller_id,
                sender_id=payment.user.id,
                type=notification_schemas.NotificationType.saleNotification,
                item_id=sale.shop_item.id
            )
            notification_content = notification_crud.get_notification_data(
                notification_schema.type,
                {"sender_name": payment.user.profile.fullname}
            )
            background_tasks.add_task(notification_crud.send_local_notification,notification_schema,db,payment.user.id)
            background_tasks.add_task(notification_crud.send_push_notification,notification_schema,notification_content.get("headings"),notification_content.get("contents"),db)


        for sale in sales:
            notificationCreateSchema = notification_schemas.NotificationBase(
                receiver_id=sale.shop_item.owner_id,
                type=notification_schemas.NotificationType.ItemSale,
            )
            notificationData = notification_crud.get_notification_data(
                notificationCreateSchema.type,
                {"sender_name": payment.user.profile.fullname}
            )
            background_tasks.add_task(
                notification_crud.send_local_notification,
                notificationCreateSchema,
                db,
                payment.user.id
            )
            background_tasks.add_task(
                notification_crud.send_push_notification,
                notificationCreateSchema,
                notificationData.get("headings"),
                notificationData.get("contents"),
                db
            )
        return {"status": True, "message": "Items purchased successfully"}

    elif payload_status == 0:
        payment.status = AllPayPaymentStatus.CANCELLED
        sales = db.query(Sales).filter(Sales.table_payment_id == payment.id).all()
        for sale in sales:
            db.delete(sale)
        db.commit()
        return {"status": True, "message": "Sales deleted due to payment cancellation"}


# def payment_webhook(background_tasks: BackgroundTasks, request: Request, data: dict, db: Session):
#     status_map = {
#         1: AllPayPaymentStatus.SUCCESS.value,
#         0: AllPayPaymentStatus.CANCELLED.value
#     }
#
#     payload_status = data.get("status")
#     client_email = data.get("client_email")
#
#     payment = db.query(AllPayPayment).join(User).filter(
#         User.email_address == client_email,
#         AllPayPayment.status == AllPayPaymentStatus.PENDING
#     ).order_by(AllPayPayment.id.desc()).first()
#
#     if not payment:
#         return {"status": False, "message": "payment record not found"}
#
#     payment.webhook_payload = data
#
#     if payload_status in status_map:
#         payment.status = status_map[payload_status]
#     else:
#         return {"status": False, "message": "Unknown status value"}
#
#     db.commit()
#
#     sales = db.query(Sales).filter(Sales.table_payment_id == payment.id).all()
#
#     if payload_status == 1:
#         for sale in sales:
#             sale.sale_status = "Shipped"
#             shop_item = db.query(ShopItem).filter_by(id=sale.item_id).first()
#             if shop_item:
#                 shop_item.is_sold = True
#                 db.add(shop_item)
#
#             db.add(sale)
#         db.commit()
#
#         for sale in sales:
#             notificationCreateSchema = notification_schemas.NotificationBase(
#                 receiver_id=sale.shop_item.owner_id,
#                 type=notification_schemas.NotificationType.ItemSale,
#             )
#             notificationData = notification_crud.get_notification_data(
#                 notificationCreateSchema.type,
#                 {"sender_name": payment.user.profile.fullname}
#             )
#             background_tasks.add_task(
#                 notification_crud.send_local_notification,
#                 notificationCreateSchema,
#                 db,
#                 payment.user.id
#             )
#             background_tasks.add_task(
#                 notification_crud.send_push_notification,
#                 notificationCreateSchema,
#                 notificationData.get("headings"),
#                 notificationData.get("contents"),
#                 db
#             )
#         return {"status": True, "message": "Items purchased successfully"}
#
#     elif payload_status == 0:
#         sales = db.query(Sales).filter(Sales.table_payment_id == payment.id).all()
#         for sale in sales:
#             db.delete(sale)
#         db.commit()
#         return {"status": True, "message": "Sales deleted due to payment cancellation"}

def get_subscription_payment_url(user: User, final_price, order_id):
    from constants import HOST
    payload = {
        "login": ALL_PAY_LOGIN_KEY,
        "order_id": order_id,
        "amount": float(final_price),
        "currency": "NIS",
        "client_name": user.email_address.split('@')[0],
        "client_email": user.email_address,
        "success_url": f"{HOST}/api/v1/subscription/boost/success/{order_id}",
        "fail_url": f"{HOST}/api/v1/subscription/boost/failed/{order_id}"
    }

    payload["sign"] = get_api_signature(payload, ALL_PAY_API_KEY)

    try:
        response = requests.post(ALL_PAY_PAYMENT_API_URL, json=payload)
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Request failed: {str(e)}")

    apppay_url = data.get("payment_url")
    if not apppay_url:
        raise HTTPException(status_code=400, detail="Unable to create payment due to technical issue please try again later.")

    return data

def get_featured_subscription_payment_url(user: User, final_price, order_id):
    from constants import HOST
    payload = {
        "login": ALL_PAY_LOGIN_KEY,
        "order_id": order_id,
        "amount": float(final_price),
        "currency": "NIS",
        "client_name": user.email_address.split('@')[0],
        "client_email": user.email_address,
        "success_url": f"{HOST}/api/v1/subscription/featured-dressing/success/{order_id}",
        "fail_url": f"{HOST}/api/v1/subscription/featured-dressing/failed/{order_id}"
    }

    payload["sign"] = get_api_signature(payload, ALL_PAY_API_KEY)

    try:
        response = requests.post(ALL_PAY_PAYMENT_API_URL, json=payload)
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Request failed: {str(e)}")

    apppay_url = data.get("payment_url")
    if not apppay_url:
        raise HTTPException(status_code=400, detail="Unable to create payment due to technical issue please try again later.")

    return data

def get_trending_search_subscription_payment_url(user: User, final_price, order_id):
    from constants import HOST
    payload = {
        "login": ALL_PAY_LOGIN_KEY,
        "order_id": order_id,
        "amount": float(final_price),
        "currency": "NIS",
        "client_name": user.email_address.split('@')[0],
        "client_email": user.email_address,
        "success_url": f"{HOST}/api/v1/subscription/trending-search/success/{order_id}",
        "fail_url": f"{HOST}/api/v1/subscription/trending-search/failed/{order_id}"
    }

    payload["sign"] = get_api_signature(payload, ALL_PAY_API_KEY)

    try:
        response = requests.post(ALL_PAY_PAYMENT_API_URL, json=payload)
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Request failed: {str(e)}")

    apppay_url = data.get("payment_url")
    if not apppay_url:
        raise HTTPException(status_code=400, detail="Unable to create payment due to technical issue please try again later.")

    return data