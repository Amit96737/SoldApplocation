from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependency import get_db
from auth.main import get_current_user
from starlette.requests import Request
from auth.models import User
from others import schemas, crud


router = APIRouter(
    prefix=""
)


@router.post(path="/user/report", tags=['Others'])
async def user_reporting(request: Request, data: schemas.CreateUserReport, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    return crud.add_user_report(
        request=request, db=db, data=data, current_user=user
    )
