from fastapi import Depends, APIRouter, Query
from typing import List
from sqlalchemy.orm import Session

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from profile import crud, schemas
from profile.schemas import ProfileEdit
from starlette.requests import Request
from starlette.background import BackgroundTasks

router = APIRouter(
    prefix="/profile",
)


@router.get("", tags=["Profile"], response_model=schemas.ProfileInDb)
async def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.get_user_profile_schema(current_user, db, current_user.id)


@router.get("/all_profile", tags=["Profile"], response_model=List[schemas.ProfileInDb])
async def get_all_user_profiles(request: Request, db: Session = Depends(get_db)):
    return crud.get_all_user_profiles(request, db)


# to fetch follower and following details
@router.get("/followers", tags=["Profile"])
async def get_followers(
        user_id: str = Query(None),
        q: str = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return crud.get_followers_users(current_user, db, user_id, q)


@router.get("/followings", tags=['Profile'])
async def get_following(
        user_id: str = Query(None),
        q: str = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return crud.get_user_following(current_user, db, user_id, query=q)


@router.get("/{user_id}", tags=["Profile"])
async def get_profile_by_id(request: Request, user_id: str, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return crud.get_profile_by_id(request, user_id, db, current_user.id)


@router.patch("", tags=["Profile"])
async def edit_profile(request: Request, profile_data: ProfileEdit, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return crud.edit_user_profile(request, profile_data, current_user, db)

@router.post("/follow/{user_id}", tags=["Profile"])
async def follow_user(request: Request,user_id: str,background_tasks: BackgroundTasks,
                      db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    return crud.follow_user(request,user_id,current_user,db,background_tasks)


# @router.post("/follow-request/{request_id}/accept", tags=["Profile"])
# async def accept_follow_request(request: Request,
#     request_id: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     return crud.accept_follow_request(request, request_id, current_user, db)
#
# @router.post("/follow-request/{request_id}/reject", tags=["Profile"])
# async def reject_follow_request(request: Request,
#     request_id: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     return crud.reject_follow_request(request, request_id, current_user, db)

@router.post("/unfollow/{user_id}", tags=["Profile"])
async def unfollow_user(request: Request, user_id: str, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    return crud.follow_user(request, user_id, current_user, db)



