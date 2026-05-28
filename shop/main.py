from typing import List

from fastapi import Depends, APIRouter, BackgroundTasks
from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks
from starlette.requests import Request

from auth.main import get_current_user
from auth.models import User
from dependency import get_db
from shop import schemas, crud, services
from fastapi import Query
from appconfig import crud as appconfig_crud
from chats import crud as chat_crud, schemas as chat_schemas
from shippings import crud as shipping_crud
from payment import crud as payment_crud
from profile import crud as profile_crud
from search import crud as search_crud
from shop.schemas import ReportReasonBase, ReportReasonInDb, ItemReportCreate, ItemReportInDb
from shop.crud import create_report_reason, get_report_reasons, create_item_report
from shop.models import DeliveryPickUpPoint
from subscription.models import UserSubscription
from subscription.models import SubscriptionTypeEnum

router = APIRouter(
    prefix="/shop",
)


@router.get("/{user_id}/items", tags=["Shop"])
async def get_user_items_by_user_id(
        user_id: str, db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return crud.get_user_items(user_id, db)


@router.get("/{user_id}/hidden-items")
async def get_user_deactivated_items(user_id: str, db: Session = Depends(get_db),
                                     current_user: User = Depends(get_current_user)):
    return crud.get_user_deactivated_items(user_id, db)


@router.post("/item", tags=["Shop"])
async def add_item(request: Request, item_data: schemas.AddItem, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    return crud.add_item(request, item_data, current_user, db)


@router.put("/item", tags=["Shop"])
async def update_item(request: Request, item_id: str, item_data: schemas.AddItem, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    return crud.update_item(request, item_id, item_data, db)


@router.get("/item/favorites", tags=["Shop"])
async def favorite_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = crud.get_favorite_items(current_user, db)
    return items if items else []


@router.patch("/item/{item_id}", tags=['Shop'])
async def update_item(item_id: str, item_data: schemas.UpdateItem,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)
                      ):
    return crud.update_item_data(item_id=item_id, item_data=item_data, db=db, current_user=current_user)


@router.post("/item/{item_id}/favorite", tags=["Shop"])
async def favorite_item(request: Request, item_id: str, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    return crud.favorite_item(request, item_id, current_user, db)


@router.get("/brands", tags=["Shop"])
async def get_brands(db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    return crud.get_all_brands(db)


@router.get("/categories_all", tags=["Shop"])
async def get_categories_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.get_categories_all(db)


@router.get("/categories", tags=["Shop"])
async def get_all_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.get_categories(db)


@router.post("/categories", tags=["Shop"])
async def add_category(category: schemas.CategoryBase, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    return crud.add_category(category, db)


@router.get("/categories/{category_id}/subcategories", tags=["Shop"])
async def get_sub_categories(category_id: str, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    return crud.get_subcategories(category_id, db)


@router.get("/categories/{category_id}/subcategories_all", tags=["Shop"])
async def get_sub_categories_all(category_id: str, db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    return crud.get_subcategories_all(category_id, db)


@router.post("/subcategories", tags=["Shop"])
async def add_sub_category(data: schemas.SubCategoryBase, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return crud.add_subcategory(data, db)


@router.get("/subcategories/{subcategory_id}/items", tags=["Shop"])
async def get_subcategory_items(subcategory_id: str, db: Session = Depends(get_db),
                                ):
    return crud.get_subcategory_items(subcategory_id, db)


@router.get("/subcategories/{subcategory_id}/items_all", tags=["Shop"])
async def get_subcategory_items_all(subcategory_id: str, db: Session = Depends(get_db),
                                    current_user: User = Depends(get_current_user)):
    return crud.get_subcategory_items_all(subcategory_id, db)


@router.post("/subcategories/items", tags=["Shop"])
async def add_subcategory_items(subcategoryItemData: schemas.SubCategoryItemBase,
                                db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.add_subcategory_item(subcategoryItemData, db)


# new added by me (add sub categories level)
@router.get("/sub-subcategories/{subcategory_id}/items", tags=["Shop"])
async def sub_sub_category_items(subcategory_id: str, db: Session = Depends(get_db)):
    return crud.get_sub_sub_subcategory_items(subcategory_id, db)


@router.get("/sub-subcategories/level/{subcategory_id}/items", tags=["Shop"])
async def sub_sub_category_items(subcategory_id: str, db: Session = Depends(get_db)):
    return crud.get_sub_sub_subcategory_level_items(subcategory_id, db)


# end sub categories level

@router.get("/sizes", tags=["Shop"])
async def get_sizes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return crud.get_sizes(db)


@router.post("/sizes", tags=["Shop"])
async def add_size(size: str, db: Session = Depends(get_db)):
    return crud.add_size(size, db)


@router.get("/colors", tags=["Shop"])
async def get_colors(db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    return crud.get_colors(db)


@router.post("/item/buy", tags=["Shop"])
async def buy_item(request: Request, buy_data: schemas.BuyItem, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return crud.buy_item(request, buy_data, current_user, db)


@router.post("/item/{item_id}/mark-as-sold", tags=["Shop"])
async def mark_as_sold(request: Request, item_id: str, current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    return crud.mark_as_sold(request, item_id, current_user, db)


@router.get("/sales", tags=["Shop"])
async def get_shop_sales(current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    return crud.get_shop_sales(current_user, db)


@router.get("/purchased", tags=["Shop"])
async def get_purchased_items(current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    return crud.get_purchased_item(current_user, db)


@router.post("/sales/{sale_id}", tags=["Shop"])
async def update_sale_status(background_tasks: BackgroundTasks, sale_id: str, sale_status: schemas.SaleStatus,
                             current_user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    return crud.update_shop_sale(background_tasks, sale_id, sale_status, current_user, db)


@router.delete("/sales/{sale_id}", tags=["Shop"])
async def delete_shipped_sale(sale_id: str, current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    return crud.delete_shipped_sale(sale_id, current_user, db)


@router.get("/item/most-popular/{category}", tags=["Shop"])
async def get_most_popular_items(category: str = "all", language_code: str = "en", current_user: User = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    return crud.get_popular_items(category, db, language_code, current_user)


@router.get("/item/{item_id}", tags=["Shop"])
async def get_item_details(request: Request, item_id: str, query: str = Query(None),
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    return crud.get_item_details(query, request, item_id, current_user, db)


# @router.get("/most-popular-item/", tags=["Shop"], response_model=list[schemas.ShopItemDetails])
# async def get_most_popular_items(current_user: User = Depends(get_current_user),
#                                  db: Session = Depends(get_db)):
#     return crud.get_popular_items(current_user, db)


@router.get("/bundles/{user_id}", tags=["Shop Bundles"])
async def get_shop_bundles(request: Request, user_id: str, db: Session = Depends(get_db)):
    return crud.get_shop_bundle(request, user_id, db)


@router.put("/bundle", tags=["Shop Bundles"])
async def update_shop_bundle(bundle_data: schemas.ShopBundleUpdate, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    return crud.update_shop_bundle(bundle_data, current_user, db)


@router.get("/explore", tags=["Shop"])
async def get_following_statuses(db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    return crud.get_explore_list(current_user, db)


@router.get("/item/posted-recently/{category}", tags=["Shop"])
async def get_posted_recently_items(category: str = 'All', current_user: User = Depends(get_current_user),
                                    db: Session = Depends(get_db)):
    return crud.get_posted_recently_items(category, db, current_user)

@router.get("/featured-dressing", tags=["Shop"])
async def get_items_by_seller(db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    return crud.featured_dressing_item(db, current_user)

# @router.get("/shoes-list", tags=["Shop"])
# async def shoes_details(
#         size: str = Query(None),
#         db: Session = Depends(get_db),
#         current_user: User = Depends(get_current_user)
# ):
#     return crud.shoes_listing_detail(db, current_user, size)

@router.get(path="/shoes-sizes", tags=['Shop'])
async def get_shoes_sizes(db: Session = Depends(get_db)):
    return crud.shoes_sizes(db=db)

@router.get(path="/home", tags=['Home'])
async def home_page_apis(
        request: Request,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        category: str = Query("all"),
        language_code: str = Query(None)
):
    background_tasks.add_task(services.insert_log_app_open, db, current_user)

    if not language_code:
        language_code = "en"

    user_subscriptions = db.query(UserSubscription).filter_by(user_id=current_user.id).all()
    seller_subscription = False
    rental_subscription = False

    for sub in user_subscriptions:
        if sub.subscription_type == SubscriptionTypeEnum.SELLER:
            seller_subscription = True

        if sub.subscription_type == SubscriptionTypeEnum.SELLER:
            rental_subscription = True

    favorites_items = crud.get_favorite_items(current_user, db)
    return {
        # "most_popular": crud.get_popular_items(category, current_user, db, language_code),
        "most_popular": crud.get_popular_items(
            category=category,
            db=db,
            language_code=language_code,
            user=current_user
        ),
        "home_slider": appconfig_crud.get_home_slider(db),
        "chat_rooms": chat_crud.get_user_chat_rooms(current_user=current_user, db=db, request=request),
        "explore": crud.get_explore_list(current_user, db),
        "categories_all": crud.get_categories_all(db),
        "recently_posted": crud.get_posted_recently_items("all", current_user=current_user, db=db),
        "trending_search": search_crud.get_trending_result(db),
        "brands": crud.get_items_available_brands(db),
        "colors": crud.get_colors(db),
        "purchased": crud.get_purchased_item(current_user, db),
        "bundles": crud.get_shop_bundle(request, current_user.id, db),
        "shipping": shipping_crud.user_shipping_info(current_user, db),
        "payment": payment_crud.user_payment_details(current_user.id, db),
        "favorite_items": favorites_items,
        "category_suggestion": crud.category_suggestion(db),
        "recently_viewed": crud.get_recently_viewed_schema(db, current_user.id),
        "shoes_list": crud.shoes_listing_detail(db),
        "featured_dressing": crud.featured_dressing_item(db, current_user),
        "seller_subscription": seller_subscription,
        "rental_subscription": rental_subscription
    }

@router.get(path="/guest-home", tags=['Home'])
async def home_page_apis(
        request: Request,
        db: Session = Depends(get_db),
        category: str = Query("all"),
        language_code: str = Query(None)
):
    if not language_code:
        language_code = "en"

    return {
        "most_popular": crud.get_popular_items(category=category, db=db, language_code=language_code),
        "home_slider": appconfig_crud.get_home_slider(db),
        "categories_all": crud.get_categories_all(db),
        "recently_posted": crud.get_posted_recently_items("all", db),
        "trending_search": search_crud.get_trending_result(db),
        "brands": crud.get_items_available_brands(db),
        "colors": crud.get_colors(db),
        "category_suggestion": crud.category_suggestion(db),
        "shoes_list": crud.shoes_listing_detail(db)
    }


@router.get(path="/hide-item/{item_id}")
async def deactivate_activate_item(
        item_id: str, db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return crud.item_hide(item_id=item_id, user=current_user, db=db)


@router.get(path="/materials", tags=['Shop'], response_model=List[schemas.ItemMaterialSchema])
async def get_materials(db: Session = Depends(get_db)):
    return crud.get_all_items_materials(db)

# @router.post("/rent", response_model=schemas.RentalOut)
# def create_rental(
#     rental: schemas.RentalCreate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
#     ):
#     return crud.create_rental(rental, db, user=current_user)

@router.get("/item/buy/{status}", tags=["Shop"])
async def payment_success(
        status: str,
        item_id: str
):
    if status == "payment-success":
        return {"message": "Payment successfully completed", "item_id": item_id}

    return {"message": "Payment failed", "item_id": item_id}

@router.get(path="/reasons-details", tags=['Shop'], response_model=list[ReportReasonInDb])
def list_report_reasons(db: Session = Depends(get_db)):
    return get_report_reasons(db)

@router.post(path="/report-reasons", tags=['Shop'], response_model=schemas.ReportReasonInDb)
def create_reason(payload: ReportReasonBase, db: Session = Depends(get_db)):
    return create_report_reason(db, payload)

@router.post("/item/report", tags=['Shop'], response_model=ItemReportInDb,)
def report_item(payload: ItemReportCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return create_item_report(db=db, user_id=current_user.id, payload=payload)

# @router.get(path="/pickup-points", tags=['Shop'])
# def list_pickup_points(city: str, db: Session = Depends(get_db)):
#     query = db.query(DeliveryPickUpPoint)
#
#     if city:
#         query = query.filter(DeliveryPickUpPoint.city == city)
#
#     return query.all()

