from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from shippings import crud, schemas
from starlette.requests import Request
from admin.services import require_login
from typing import List

router = APIRouter(
    prefix="/shipping",
)


@router.get("", tags=["Shipping"])
async def get_user_shipping_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.get_shipping_info(current_user, db)


@router.patch("", tags=["Shipping"])
async def modify_shipping_details(request: Request, shipping_info: schemas.ShippingEdit, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    return crud.modify_shipping_details(request, shipping_info, current_user, db)


@router.get("/get-pickup-location", tags=["Shipping"], response_model=List[schemas.PickUpPoint])
async def get_user_pickup_location(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.user_near_pickup_points(user=current_user, db=db)


@router.get(path="/meeting-points", tags=['Shipping'], response_model=List[schemas.MeetingPointDetails])
async def get_meeting_points(db: Session = Depends(get_db)):
    return crud.get_meeting_points(db)


# current_user=Depends(require_login),

@router.post(path="/meeting-points", tags=['Shipping'], response_model=schemas.MeetingPointDetails)
async def create_meeting_point(data: schemas.MeetingPoint,
                               db: Session = Depends(get_db),
                               ):
    return crud.create_meeting_point(db=db, data=data)
