import operator
from sqlalchemy import or_, func
from fastapi.encoders import jsonable_encoder
from search import models, schemas
from shop.models import ShopItem, SearchSuggestion
from sqlalchemy.orm import Session
from forum.models import ForumTopic
from forum.schemas import TopicInDb
import json
from datetime import datetime, timedelta
from auth.models import User, AccountStatus
from subscription import crud as subscription_crud, models as subscription_model
from exception import UnicornException
from starlette import status
from shop import crud as shop_crud
from profile import models as profile_models, crud as profile_crud


# def search(query: str, db: Session):
#     existing_query = (db.query(models.SearchSuggestions)
#                       .filter(models.SearchSuggestions.query.ilike(f"%{query}%")).first())
#
#     if not existing_query:
#         new_search = models.SearchSuggestions(query=query)
#         db.add(new_search)
#         db.commit()
#         db.refresh(new_search)
#     else:
#         existing_query.views += 1
#         db.commit()
#
#     result = (db.query(ShopItem).filter (or_(ShopItem.title.ilike(f"%{query}%"),
# #                                               ShopItem.category.ilike(f"%{query}%"),
#                                               ShopItem.sub_category.ilike(f"%{query}%"),
#                                               ShopItem.description.ilike(f"%{query}%"),
#                                               ShopItem.brand.ilike(f"%{query}%")
#                                               )
#                                         ).filter(ShopItem.is_sold ==False).all())
#     return result

# def search(query: str, db: Session):
#     existing_query = db.query(models.SearchSuggestions).filter(models.SearchSuggestions.query.ilike(query)).first()
#     if not existing_query:
#         new_search = models.SearchSuggestions(query=query)
#         db.add(new_search)
#         db.commit()
#         db.refresh(new_search)
#     else:
#         existing_query.views += 1
#         db.commit()

# def get_suggestions(query: str, db: Session):
#     suggestionsInDb = db.query(models.SearchSuggestions).all()
#     querySuggestions = [
#         schemas.SearchResult(
#             query=suggestion.query,
#             views=suggestion.views
#
#         ) for suggestion in suggestionsInDb if query.lower() in suggestion.query.replace("'s", "").lower().split(" ")
#     ]
#
#     key = operator.itemgetter("views")
#     return sorted(jsonable_encoder(querySuggestions), key=key, reverse=True)


def get_match_titles(query: str, db: Session):
    items = db.query(ShopItem).outerjoin(
        SearchSuggestion, ShopItem.id == SearchSuggestion.item_id
    ).filter(
        or_(
            ShopItem.title.ilike(f"%{query}%"),
            ShopItem.brand.ilike(f"%{query}%"),
            ShopItem.category.ilike(f"%{query}%"),
            SearchSuggestion.term.ilike(f"%{query}%")
        )
    ).all()
    titles = list(set([i.title for i in items]))
    return titles


def get_items_filter(db: Session, query: str = None, brand: str = None, item_type: str = None, category: str = None,
                     title: str = None, materials: str = None, hash_tags=None):
    filters = [ShopItem.is_sold == False]

    if query:
        filters.append(
            or_(
                ShopItem.title.ilike(f"%{query}%"),
                ShopItem.brand.ilike(f"%{query}%"),
                ShopItem.category.ilike(f"%{query}%"),
                ShopItem.sub_category.ilike(f"%{query}%"),
                ShopItem.description.ilike(f"%{query}%"),
                ShopItem.type.ilike(f"%{query}%"),
                ShopItem.hash_tags.ilike(f"%{query}%"),
                SearchSuggestion.term.ilike(f"%{query}%")
            )
        )

    if brand and not query:
        filters.append(ShopItem.brand.ilike(f"%{brand}%"))
        ItemsInDb = db.query(ShopItem).filter(*filters).all()
        return [shop_crud.get_item_schema(item, db) for item in ItemsInDb] if len(ItemsInDb) > 10 else []
    elif brand and query:
        filters.append(ShopItem.brand.ilike(f"%{brand}%"))

    if item_type:
        filters.append(ShopItem.type.ilike(f"%{item_type}%"))

    if category:
        filters.append(ShopItem.category.ilike(f"%{category}%"))

    if title:
        filters.append(ShopItem.title.ilike(f"%{title}%"))
    if hash_tags:
        filters.append(ShopItem.hash_tags.ilike(f"%{hash_tags}%"))

    if materials:
        try:
            # material_list = [i.strip().lower() for i in materials.split(",")]
            # for i in material_list:
            filters.append(ShopItem.material.ilike(f"%{materials}%"))
        except Exception as e:
            print(e)

    member_suggestion = user_or_member_suggestion(query=query, db=db)

    return {"items": [shop_crud.get_item_schema(item, db) for item in db.query(ShopItem).outerjoin(
            SearchSuggestion, ShopItem.id == SearchSuggestion.item_id).filter(*filters).all() if
            not item.owner.preferences.holiday_mode and item.owner.account_status is AccountStatus.Enabled and item.is_sold is False
            ],
            "users":  member_suggestion
            }


def get_popular_suggestions(db: Session):
    suggestions_in_db = db.query(models.SearchSuggestions).all()

    query_suggestions = [
        schemas.SearchResult(
            query=suggestion.query,
            views=suggestion.views
        )
        for suggestion in suggestions_in_db
    ]

    sorted_suggestions = sorted(query_suggestions, key=operator.attrgetter("views"), reverse=True)
    return jsonable_encoder(sorted_suggestions[:5])


def get_trending_topics(db: Session):
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    trending_topics = (
        db.query(ForumTopic)
        .filter(ForumTopic.date_created >= seven_days_ago)
        .order_by(ForumTopic.date_created.desc())
        .all()
    )

    result = []
    for topic in trending_topics:
        topic_dict = topic.__dict__.copy()
        topic_dict['images'] = json.loads(topic_dict.get('images', '[]'))
        result.append(TopicInDb(**topic_dict))

    return result


def get_trending_result(db: Session):
    # if subscription_crud.is_user_subscription_active(
    #         db=db, user_id=current_user.id,
    #         subscription_type=subscription_model.SubscriptionTypeEnum.TRENDING_SEARCH.value
    # ):
    forum_result = (
        db.query(
            ShopItem
        )
        .outerjoin(ShopItem.forum)
        .group_by(ShopItem.id)
        .having(func.count(ForumTopic.id) > 0)
        .order_by(func.count(ForumTopic.id).desc())
        .all()

    )

    result = db.query(ShopItem).filter(ShopItem.view_count > 0).order_by(
        ShopItem.view_count.desc()).all() + forum_result
    return [shop_crud.get_item_schema(item, db) for item in result]


def user_or_member_suggestion(query: str, db: Session):
    users = db.query(User).join(profile_models.Profile.user).filter(
        or_(
            profile_models.Profile.fullname.ilike(f"%{query}%"),
            profile_models.Profile.username.ilike(f"%{query}%"),
            profile_models.Profile.nickname.ilike(f"%{query}%"),
            User.email_address.ilike(f"%{query}%")
        )
    ).all()

    return [profile_crud.get_user_profile_schema(user, db) for user in users]
