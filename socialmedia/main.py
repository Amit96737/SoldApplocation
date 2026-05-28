from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from socialmedia import schemas, crud

router = APIRouter(
    prefix="/social-media",
)


@router.post("/status", tags=["Social Media"])
async def post_status(status_data: schemas.PostStatus, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    return crud.post_status(status_data, db, current_user)


@router.get("/{user_id}/statuses", tags=["Social Media"])
async def post_status(user_id: str, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    return crud.get_status(user_id, db, current_user)
