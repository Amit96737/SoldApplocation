from subscription import models, schemas
from datetime import datetime, timedelta
from exception import UnicornException
from starlette import status
from I18n.load_language import get_lang_content
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from profile import crud as profile_crud
from affiliated import crud as affiliate_crud
from starlette.background import BackgroundTasks
from fastapi.responses import JSONResponse
from payment import crud as payment_crud
from shop import models as shop_model
from decimal import Decimal
from datetime import datetime, timedelta
import random
from subscription.models import SubscriptionTypeEnum
import uuid

from subscription.models import UserSubscription

FEATURED_DRESSING_PRICE = 29
SUBSCRIPTION_VALIDITY_DAYS = 30

TRENDING_SEARCH_PRICE = 30
TRENDING_SEARCH_VALIDITY_DAYS = 30

def check_plain(db, plan_id):
    try:
        plan = db.query(models.SubscriptionPlan).filter(
            models.SubscriptionPlan.id == plan_id,
            models.SubscriptionPlan.is_active == True
        ).first()
        if plan:
            return plan
    except Exception as e:
        print(e)
    return False



def is_subscription_active(db: Session, user_id: str, subscription_type: models.SubscriptionTypeEnum) -> bool:
    return db.query(models.UserSubscription).filter(
        models.UserSubscription.user_id == user_id,
        models.UserSubscription.subscription_type == subscription_type,
        models.UserSubscription.expire_on != None,
        models.UserSubscription.expire_on >= datetime.utcnow()
    ).first() is not None


def subscription_active(db: Session, user_id: str, subscription_type: models.SubscriptionTypeEnum):
    return db.query(models.UserSubscription).filter(
        models.UserSubscription.user_id == user_id,
        models.UserSubscription.subscription_type == subscription_type,
        models.UserSubscription.expire_on != None,
        models.UserSubscription.expire_on >= datetime.utcnow()
    ).first()


def user_check_subscriptions(db: Session, user_id: str):
    return{
        "is_seller": is_subscription_active(db, user_id, models.SubscriptionTypeEnum.SELLER),
        "is_featured_dressing": is_subscription_active(db, user_id, models.SubscriptionTypeEnum.FEATURED_DRESSING),
        "is_trending_search": is_subscription_active(db, user_id, models.SubscriptionTypeEnum.TRENDING_SEARCH),
        "is_boosted_visibility": is_subscription_active(db, user_id, models.SubscriptionTypeEnum.BOOSTED_VISIBILITY),
        "is_rental": is_subscription_active(db, user_id, models.SubscriptionTypeEnum.SELLER),
    }


def get_active_subscription(db: Session, user_id: str):
    seller_subscription = subscription_active(db, user_id, models.SubscriptionTypeEnum.SELLER)
    featured_dressing = subscription_active(db, user_id, models.SubscriptionTypeEnum.FEATURED_DRESSING)
    trending_search = subscription_active(db, user_id, models.SubscriptionTypeEnum.TRENDING_SEARCH)
    boosted_visibility = subscription_active(db, user_id, models.SubscriptionTypeEnum.BOOSTED_VISIBILITY)
    rental_subscription = subscription_active(db, user_id, models.SubscriptionTypeEnum.SELLER)

    return {
        "seller": schemas.SubscribeSchemaOut.model_validate(seller_subscription).model_dump() if seller_subscription else None,
        "featured_dressing": schemas.SubscribeSchemaOut.model_validate(featured_dressing).model_dump() if featured_dressing else None,
        "trending_search": schemas.SubscribeSchemaOut.model_validate(trending_search).model_dump() if trending_search else None,
        "boosted_visibility": schemas.SubscribeSchemaOut.model_validate(boosted_visibility).model_dump() if boosted_visibility else None,
        "rental_subscription": schemas.SubscribeSchemaOut.model_validate(rental_subscription).model_dump() if rental_subscription else None,
    }

def user_subscribe(user, db, body: schemas.SubscribeSchema, request: Request,):
    if is_subscription_active(db=db, user_id=user.id, subscription_type=body.SubscriptionType):
        raise UnicornException(status_code=400,message=f"Your plan is currently already active.")

    platform = "apple" if body.verificationData is None or body.verificationData.source == "apple" else "android"

    if platform == "android":
        if not body.verificationData or body.verificationData.source != "google_play":
            raise HTTPException(status_code=400, detail="Unsupported platform, expected google_play for Android")

        # purchase_token = body.verificationData.serverVerificationData
        product_id = body.productId
        # purchase_id = body.purchaseId
        transaction_date = datetime.fromtimestamp(body.transactionDate / 1000)
        status = "active" if body.status == "PurchaseStatus.purchased" else "expired"
        auto_renewing = body.verificationData.localVerificationData.get("autoRenewing", False)

        expiry_date = datetime.fromtimestamp((body.transactionDate / 1000) + 30 * 24 * 60 * 60)
        # receipt = purchase_token

    elif platform == "apple":
        if not body.transactionId or not body.expiresDate:
            raise HTTPException(status_code=400, detail="Missing required fields for Apple: transactionId, expiresDate")

        # receipt = body.purchaseId or body.transactionId
        product_id = body.productId
        transaction_date = datetime.fromtimestamp(body.transactionDate / 1000) if body.transactionDate else datetime.utcnow()
        expiry_date = datetime.fromtimestamp(body.expiresDate / 1000)
        status = "active" if expiry_date > datetime.utcnow() else "expired"
        auto_renewing = True
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform it should be apple or google_play")

    subscription = models.UserSubscription(
        user_id=user.id,
        subscription_type=body.SubscriptionType,
        body=body.model_dump(),
        platform=platform,
        product_id=product_id,
        status=status,
        expire_on=expiry_date,
        auto_renewing=auto_renewing,
        transaction_date=transaction_date
    )
    db.add(subscription)
    db.commit()
    return JSONResponse(
        content={
            "message": "subscription added successfully.",
            "data": schemas.SubscribeSchemaOut.model_validate(subscription).model_dump()
        }
    )

# def create_user_subscription(plan_id, db: Session, user_id):
#     plainInDB = check_plain(db, plan_id)
#     if plainInDB.is_weekly:
#         day = 7 * plainInDB.duration
#     else:
#         day = 30 * plainInDB.duration
#
#     new_subscription = models.UserSubscription(
#         plain_id=plan_id,
#         user_id=user_id,
#         subscribe_at=datetime.utcnow(),
#         expire_on=datetime.utcnow() + timedelta(days=day)
#     )
#     db.add(new_subscription)
#     db.commit()
#     db.refresh(new_subscription)
    # if plan.affiliate_code:
    #     background_tasks.add_task(affiliate_crud.reward_of_affiliate_code, db, plan.affiliate_code, user.id,
    #                               new_subscription.id, plainInDB.price)

# def featured_dressing_users(db: Session):
#     featured_user = (db.query(models.UserSubscription)
#                      .join(models.UserSubscription.plan)
#                      .filter(models.UserSubscription.expire_on >= datetime.utcnow(),
#                              models.SubscriptionPlan.subscription_type == models.SubscriptionTypeEnum.FEATURED_DRESSING)).all()
#
#     return [profile_crud.get_user_profile_schema(user.user, db) for user in featured_user]

from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import select, func
import random


BOOST_PRICES = {
    shop_model.BoostDuration.DAYS_3: {
        "base": Decimal("0.04"),
        "min_price": Decimal("1.8")
    },
    shop_model.BoostDuration.DAYS_7: {
        "base": Decimal("0.055"),
        "min_price": Decimal("2.8")
    },
}

TAX_PERCENT = Decimal("0.18")
DISCOUNT_PERCENT = Decimal("0.10")


def boost_visibility_item(
        data: schemas.BoostItemIn,
        current_user,
        db: Session,
        request
):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    order_id = ''.join(str(d) for d in random.sample(range(10), 8))
    cfg = BOOST_PRICES.get(data.day, 3)
    base_percent = cfg["base"]
    tax_percent = TAX_PERCENT
    final_percent = base_percent + (base_percent * tax_percent)

    price = 0
    for item_id in data.item:
        shop_item = db.query(shop_model.ShopItem).filter(
            shop_model.ShopItem.id==item_id, shop_model.ShopItem.owner_id == current_user.id
        ).first()

        if not shop_item:
            raise HTTPException(status_code=404, detail="Invalid item does not found.")

        item_boost_count = db.query(shop_model.ItemBoost).filter(
            shop_model.ItemBoost.shop_item_id == item_id
        ).count()

        if item_boost_count >= 1:
            final_percent = final_percent * (Decimal("1") - DISCOUNT_PERCENT)
        item_price = Decimal(str(shop_item.price))
        boost_price = item_price * final_percent

        # apply minimum price rule
        min_price = cfg["min_price"]
        if boost_price < min_price:
            boost_price = min_price

        if data.day == shop_model.BoostDuration.DAYS_3:
            end_at = datetime.utcnow() + timedelta(days=3)
        else:
            end_at = datetime.utcnow() + timedelta(days=7)

        new_boost = shop_model.ItemBoost(
            shop_item_id=item_id,
            boost_duration=data.day,
            base_percent=base_percent,
            tax_percent=tax_percent,
            final_percent_with_tax=final_percent,
            price=int(boost_price),
            start_at=datetime.utcnow(),
            end_at=end_at,
            order_id=order_id,
        )

        db.add(new_boost)
        db.commit()

        price += boost_price

    payment_data = payment_crud.get_subscription_payment_url(user=current_user, final_price=price, order_id=order_id)

    all_pay_url = payment_data.get("payment_url")

    return {"message": language_content.get("payment url create successfully"), "status": True,
            "payment_url": all_pay_url, "price": price}


def handle_payment(db: Session, order_id: str, action):
    # Get all item boosts for this order
    item_boosts = db.query(shop_model.ItemBoost).filter(
        shop_model.ItemBoost.order_id == order_id
    ).all()

    # Check if order exists
    if not item_boosts:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Order not found"
            }
        )

    # Check payment status using first item (all should have same status)
    first_item_boost = item_boosts[0]  # Use index since .all() returns list
    if first_item_boost.payment_status != "pending":
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Payment status was already updated"
            }
        )

    try:
        if action == "success":
            for boost in item_boosts:
                boost.payment_status = "completed"
                boost.is_active = True

                # Update the associated shop item to be boosted
                shop_item = db.query(shop_model.ShopItem).filter(
                    shop_model.ShopItem.id == boost.shop_item_id
                ).first()
                if shop_item:
                    shop_item.is_boosted = True

            db.commit()
            print(f"Activated {len(item_boosts)} boosts for order {order_id}")

        elif action == "failed":
            for boost in item_boosts:
                boost.payment_status = "failed"
                boost.is_active = False

            db.commit()
            print(f"Marked {len(item_boosts)} boosts as failed for order {order_id}")

        else:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Invalid action"
                }
            )

        return JSONResponse(
            status_code=200,
            content={
                "detail": f"Your payment has been {action}"
            }
        )

    except Exception as e:
        db.rollback()
        print(f"Error processing payment for order {order_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error"
            }
        )

# def buy_featured_dressing(
#         request,
#         current_user,
#         db: Session,
# ):
#     active_subscription = db.query(UserSubscription).filter(
#         UserSubscription.user_id == current_user.id,
#         UserSubscription.subscription_type == SubscriptionTypeEnum.FEATURED_DRESSING,
#         UserSubscription.status == "active",
#         UserSubscription.expire_on > datetime.utcnow()
#     ).first()
#
#     if active_subscription:
#         return JSONResponse(
#             status_code=400,
#             content={
#                 "detail": "You already have an active Featured Dressing subscription"
#             }
#         )
#     order_id = ''.join(str(d) for d in random.sample(range(10), 8))
#
#     subscription = UserSubscription(
#         id=str(uuid.uuid4()),
#         user_id=current_user.id,
#         subscription_type=SubscriptionTypeEnum.FEATURED_DRESSING,
#         subscribe_at=datetime.utcnow(),
#         expire_on=datetime.utcnow() + timedelta(days=SUBSCRIPTION_VALIDITY_DAYS),
#         status="pending",
#         product_id="sold_featured_dressing_monthly_subscription",
#         platform="android",
#         auto_renewing=False,
#         transaction_date=datetime.utcnow()
#     )
#
#     db.add(subscription)
#     db.commit()
#
#     payment_data = payment_crud.get_featured_subscription_payment_url(
#         user=current_user,
#         final_price=FEATURED_DRESSING_PRICE,
#         order_id=order_id
#     )
#
#     pay_url = payment_data.get("payment_url")
#
#     return {
#         "status": True,
#         "message": "Subscription created successfully",
#         "payment_url": pay_url,
#         "price": FEATURED_DRESSING_PRICE,
#     }

def buy_featured_dressing(request, current_user, db: Session):
    active_subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.subscription_type == SubscriptionTypeEnum.FEATURED_DRESSING,
        UserSubscription.status == "active",
        UserSubscription.expire_on > datetime.utcnow()
    ).first()

    if active_subscription:
        return JSONResponse(status_code=200, content={"detail": "You already have an active Featured Dressing subscription"})

    pending_subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.subscription_type == SubscriptionTypeEnum.FEATURED_DRESSING,
        UserSubscription.status == "pending"
    ).first()

    if pending_subscription:
        payment_data = payment_crud.get_featured_subscription_payment_url(
            user=current_user,
            final_price=FEATURED_DRESSING_PRICE,
            order_id=pending_subscription.id
        )

        return {"status": True, "message": "Payment pending", "payment_url": payment_data.get("payment_url"), "price": FEATURED_DRESSING_PRICE}

    subscription = UserSubscription(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        subscription_type=SubscriptionTypeEnum.FEATURED_DRESSING,
        subscribe_at=datetime.utcnow(),
        expire_on=datetime.utcnow() + timedelta(days=SUBSCRIPTION_VALIDITY_DAYS),
        status="pending",
        product_id="sold_featured_dressing_monthly_subscription",
        platform="android",
        auto_renewing=False,
        transaction_date=datetime.utcnow()
    )

    db.add(subscription)
    db.commit()

    payment_data = payment_crud.get_featured_subscription_payment_url(
        user=current_user,
        final_price=FEATURED_DRESSING_PRICE,
        order_id=subscription.id
    )

    return {"status": True, "message": "Subscription created successfully", "payment_url": payment_data.get("payment_url"), "price": FEATURED_DRESSING_PRICE}

def handle_featured_dressing_payment(db: Session, action, order_id: str):
    subscription = db.query(UserSubscription).filter(
        UserSubscription.product_id == "sold_featured_dressing_monthly_subscription"
    ).first()

    if not subscription:
        return JSONResponse(
            status_code=404,
            content={"detail": "Order not found"}
        )

    if subscription.status != "pending":
        return JSONResponse(
            status_code=400,
            content={"detail": "Payment already processed"}
        )

    try:
        if action == "success":
            subscription.status = "active"
            db.commit()

            return JSONResponse(
                status_code=200,
                content={"detail": "Payment successful. Subscription activated!"}
            )

        elif action == "failed":
            subscription.status = "failed"
            db.commit()

            return JSONResponse(
                status_code=200,
                content={"detail": "Payment failed. Subscription cancelled."}
            )

        else:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid action"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

def buy_trending_search_subscription(
        request,
        current_user,
        db: Session,
):
    active_subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.subscription_type == SubscriptionTypeEnum.TRENDING_SEARCH,
        UserSubscription.expire_on > datetime.utcnow()
    ).first()

    if active_subscription:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "You already have an active trending search subscription"
            }
        )
    order_id = ''.join(str(d) for d in random.sample(range(10), 8))

    subscription = UserSubscription(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        subscription_type=SubscriptionTypeEnum.TRENDING_SEARCH,
        subscribe_at=datetime.utcnow(),
        expire_on=datetime.utcnow() + timedelta(days=SUBSCRIPTION_VALIDITY_DAYS),
        status="pending",
        product_id="sold_trending_search_monthly_subscription",
        platform="android",
        auto_renewing=False,
        transaction_date=datetime.utcnow()
    )

    db.add(subscription)
    db.commit()

    payment_data = payment_crud.get_trending_search_subscription_payment_url(
        user=current_user,
        final_price=TRENDING_SEARCH_PRICE,
        order_id=order_id
    )

    pay_url = payment_data.get("payment_url")

    return {
        "status": True,
        "message": "Subscription created successfully",
        "payment_url": pay_url,
        "price": TRENDING_SEARCH_PRICE,
    }

def handle_trending_search_payment(db: Session, action, order_id: str):
    subscription = db.query(UserSubscription).filter(
        UserSubscription.product_id == "sold_trending_search_monthly_subscription"
    ).first()

    if not subscription:
        return JSONResponse(
            status_code=404,
            content={"detail": "Order not found"}
        )

    if subscription.status != "pending":
        return JSONResponse(
            status_code=400,
            content={"detail": "Payment already processed"}
        )

    try:
        if action == "success":
            subscription.status = "active"
            db.commit()

            return JSONResponse(
                status_code=200,
                content={"detail": "Payment successful. Subscription activated!"}
            )

        elif action == "failed":
            subscription.status = "failed"
            db.commit()

            return JSONResponse(
                status_code=200,
                content={"detail": "Payment failed. Subscription cancelled."}
            )

        else:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid action"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

