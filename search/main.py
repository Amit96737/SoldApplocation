from typing import Optional
from fastapi import Depends, APIRouter, Query
from sqlalchemy.orm import Session

from dependency import get_db
from search import schemas, crud
from shop.schemas import ShopItemDetails
from forum.schemas import TopicInDb
from typing import List
from auth.models import User
from auth.main import get_current_user

router = APIRouter(
    prefix="/search",
)


# @router.post("/suggestions", tags=["Search"])
# async def search(query: str, db: Session = Depends(get_db)):
#     return crud.search(query, db)

# @router.get("/suggestions", tags=["Search"])
# async def get_suggestions(query: str, db: Session = Depends(get_db)):
#     return crud.get_suggestions(query, db)


@router.get("/suggestions", tags=["Search"])
async def search_titles(query: str, db: Session = Depends(get_db),
                        ):
    titles = crud.get_match_titles(query, db)
    return titles


#  Autocomplete search
@router.get("/items", tags=["Search"])
async def get_item_detail(query: Optional[str] = None, brand: Optional[str] = None, type: Optional[str] = None,
                          category: Optional[str] = None, title: Optional[str] = None, material: str = Query(None),
                          hash_tag: str = Query(None),
                          db: Session = Depends(get_db),
                          ):
    return crud.get_items_filter(db=db, query=query, brand=brand, item_type=type, category=category,
                                 title=title, materials=material, hash_tags=hash_tag)


@router.get("/popular-suggestions", tags=["Search"])
async def get_suggestions(
        db: Session = Depends(get_db)
):
    return crud.get_popular_suggestions(db)


# @router.get("/trending-search", tags=["Search"], response_model=List[ShopItemDetails])
# async def get_trending(
#         db: Session = Depends(get_db),
#         current_user: User = Depends(get_current_user),
# ):
#     return crud.get_trending_result(db, current_user)

@router.get("/users", tags=["Search"])
async def member_suggestion_search(query: str = Query(...), db: Session = Depends(get_db)):
    return crud.user_or_member_suggestion(query, db)
