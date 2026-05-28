from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from dependency import get_db
from ratings import crud
from ratings import schemas
from auth import main as auth_main
from auth.models import User

router = APIRouter(
    prefix="/rating",
)


@router.post("", tags=["Rating"])
async def rate_user(request: Request, data: schemas.RatingCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(auth_main.get_current_user)):
    return crud.rate_user(request, data, db, current_user)


@router.get("/{user_id}", tags=["Rating"])
async def get_reviews(user_id: str, db: Session = Depends(get_db),
                      current_user: User = Depends(auth_main.get_current_user)):
    return crud.get_user_ratings(user_id, db, current_user)
