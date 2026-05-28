from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from starlette.requests import Request

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from forum import crud
from forum import schemas

router = APIRouter(
    prefix="/forum",
)


@router.post("/topic", tags=["Forum"])
async def post_topic(request: Request, topic_data: schemas.AddTopic, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    return crud.add_topic(request, topic_data, current_user, db)


@router.get("/topics", tags=["Forum"])
async def get_user_topics(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return crud.get_user_topics(current_user, db)


@router.get("/topics/{category_name}", tags=["Forum"])
async def get_topics_by_category(category_name: str, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):

    return crud.get_topics_by_category(category_name, current_user, db)


@router.post("/topic/answer", tags=["Forum"])
async def post_topic_answer(request: Request, answer_data: schemas.AddTopicAnswer, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return crud.post_topic_answer(request, answer_data, current_user, db)


@router.get("/topic/{topic_id}/answers", tags=["Forum"])
async def get_topic_answer(request: Request, topic_id: str, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return crud.get_topic_answers(request, topic_id, current_user, db)


@router.post("/topic/{topic_id}/favorite", tags=["Forum"])
async def favorite_topic(request: Request, topic_id: str, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    return crud.fav_topic(request, topic_id, current_user, db)


@router.get("/topic/favorites", tags=["Forum"])
async def get_favorite_topics(db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    return crud.get_favorite_topics(current_user, db)


@router.delete("/topic/{topic_id}", tags=["Forum"])
async def delete_topic(request: Request, topic_id: str, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return crud.delete_topic(request, topic_id, db)
