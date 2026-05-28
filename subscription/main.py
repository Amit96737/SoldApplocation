from fastapi import Depends, APIRouter, Request
from dependency import get_db
from sqlalchemy.orm import Session
from subscription import crud, schemas, models
from typing import List, Dict
from auth.models import User
from auth.main import get_current_user
from fastapi import HTTPException, status
from starlette.background import BackgroundTasks
from admin.services import get_admin_current_user
from datetime import datetime

router = APIRouter(
    prefix="/subscription",
)

@router.post("/", tags=['Subscription'])
async def user_subscription(
        request: Request,
        plan: schemas.SubscribeSchema,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    return crud.user_subscribe(user=current_user, db=db, body=plan, request=request)


@router.get("/", tags=['Subscription'], response_model=List[schemas.SubscribeSchemaOut])
def user_subscription(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    return db.query(models.UserSubscription).filter(
        models.UserSubscription.user_id == current_user.id
    )


@router.get("/active-plan/{subscription_type}", tags=['Subscription'])
def user_active_plan(
        subscription_type,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    try:
        activePlanDb = crud.get_user_subscription_active(
            db=db,
            user_id=current_user.id,
            subscription_type=subscription_type
        )
        if activePlanDb:
            return activePlanDb
    except Exception as e:
        print(f"Error fetching active plan: {e}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No active subscription plan found."
    )


@router.post("/boost-visibility")
async def boot_items(
        request: Request,
        data: schemas.BoostItemIn,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    return crud.boost_visibility_item(
        data=data,
        current_user=current_user,
        db=db,
        request=request
    )


@router.get("/boost/{action}/{order_id}")
async def update_payment_status(
        action: str,
        order_id: str,
        db: Session = Depends(get_db)
):
    return crud.handle_payment(
        db=db,
        action=action,
        order_id=order_id
    )

@router.post("/featured-dressing")
async def buy_featured_dressing(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    return crud.buy_featured_dressing(
        request=request,
        current_user=current_user,
        db=db,
    )

@router.get("/featured-dressing/{action}/{order_id}")
def featured_dressing_success(action: str, order_id: str, db: Session = Depends(get_db)):
    return crud.handle_featured_dressing_payment(
        db=db,
        order_id=order_id,
        action=action
    )

@router.get("/subscribed-users-list", tags=['Subscription'])
def get_subscribed_users(db: Session = Depends(get_db)):
    data = (db.query(models.UserSubscription).filter(models.UserSubscription.status == "active").all())
    return [obj.user_id for obj in data]

@router.post("/trending-search")
async def buy_trending_search(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    return crud.buy_trending_search_subscription(
        request=request,
        current_user=current_user,
        db=db,
    )

@router.get("/trending-search/{action}/{order_id}")
def trending_search_success(action: str, order_id: str, db: Session = Depends(get_db)):
    return crud.handle_trending_search_payment(
        db=db,
        order_id=order_id,
        action=action
    )