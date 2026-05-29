import json, random
import operator
from uuid import uuid4
from sqlalchemy import delete
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError

from starlette import status
from starlette.background import BackgroundTasks
from starlette.requests import Request
from datetime import datetime, timedelta, timezone

from I18n.load_language import get_lang_content
from auth import models as auth_models
from exception import UnicornException
from helper import calculate_average
from notification import crud as notification_crud
from notification import schemas as notification_schemas
from ratings.models import UserRatings
from shop import schemas, services
from auth.schemas import AccountStatus
from fastapi import Depends
from dependency import get_db
from sqlalchemy import or_
from shop.validations import *
from sqlalchemy import desc
from shop.models import favourited_items, ShopItem
from auth.models import User
from subscription.models import UserSubscription
from profile import crud as profile_crud
from collections import defaultdict
from payment import crud as payment_crud, schema as payment_schema
from payment.models import AllPayPayment
from shop.models import Sales
import uuid
from shop.schemas import SaleStatus
import httpx
import requests
from typing import Optional
from shop.services import get_or_create_brand, sold_item_visibility
from shop.models import ReportReason, ItemReport, ItemReportReason, ShopItem
from shop.schemas import ReportReasonBase, ItemReportCreate

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

translation_cache = {}


# client = SearchClient.create('IGNT54H4K1', '4e73d77e0b5964158547eff29aec178f')
# recommend_client = RecommendClient.create("D176ZDTM48", "3a38088f5cc563ad31b4f0d94d35636b")
# index = client.init_index('shop_items')


def translate_text(text, target_language, source_language=None):
    url = "https://translation.googleapis.com/language/translate/v2"
    api_key = "AIzaSyAbr1WQvMP1O2wCYoAvuV3XEURTfHuCBRY"
    params = {
        'q': text,
        'target': target_language,
        'format': 'text',
        'key': api_key
    }
    if source_language:
        params['source'] = source_language

    response = requests.post(url, data=params)
    result = response.json()

    if 'data' in result:
        return result['data']['translations'][0]['translatedText']
    else:
        return text


def recursive_translate(obj, lang_map, language_code):
    if isinstance(obj, dict):
        print("obj", obj.items())
        for key, value in obj.items():
            if key in ["title", "description", "last_message", "category", "sub_category", "item_title"] and isinstance(value, str):
                if value in lang_map:
                    obj[key] = lang_map[value]
                else:
                    cache_key = f"{language_code}:{value}"
                    if cache_key in translation_cache:
                        obj[key] = translation_cache[cache_key]
                    else:
                        translated = translate_text(
                            value,
                            target_language=language_code,
                            source_language="en"
                        )
                        translation_cache[cache_key] = translated
                        obj[key] = translated

            elif isinstance(value, (dict, list)):
                recursive_translate(value, lang_map, language_code)

    elif isinstance(obj, list):
        for item in obj:
            recursive_translate(item, lang_map, language_code)
    return obj


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        language_code = request.query_params.get("language_code", "en")
        if language_code not in ["en", "fr", "he"]:
            return JSONResponse(
                content={"message": "country not support this language code"}, status_code=status.HTTP_400_BAD_REQUEST)
        response = await call_next(request)
        if language_code == "en":
            return response

        if "application/json" not in response.headers.get("content-type", ""):
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        data = json.loads(body)

        if language_code != "en":
            lang_map = get_lang_content(language_code)
            data = recursive_translate(data, lang_map, language_code)

        return JSONResponse(
            content=data,
            status_code=response.status_code,
            headers=dict(response.headers)
        )

def add_item(request: Request, item_data: schemas.AddItem, current_user: User, db: Session):
    # if not is_user_subscription_active(db=db, user_id=current_user.id, subscription_type="seller"):
    #     raise UnicornException(status_code=status.HTTP_400_BAD_REQUEST,
    #                            message=f"Your seller plan is not active. please choose plan to add product.")

    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)
    unique_id = str(uuid4())

    size_cleaned = item_data.size.strip() if item_data.size else ""
    # brand_cleaned = item_data.brand.strip() if item_data.brand else ""
    brand_cleaned = item_data.brand.strip() if item_data.brand else ""

    if brand_cleaned:
        get_or_create_brand(db, brand_cleaned)

    category_cleaned = item_data.category.strip() if item_data.category else ""
    if category_cleaned and not category_exists(category_cleaned, db):
        raise UnicornException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid category: '{category_cleaned}'"
        )

    sub_category_cleaned = item_data.sub_category.strip() if item_data.sub_category else ""
    if sub_category_cleaned and not sub_category_exists(sub_category_cleaned, db):
        raise UnicornException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid sub-category: '{sub_category_cleaned}'"
        )

    colors_cleaned = [color.strip() for color in item_data.colors] if item_data.colors else []
    result = colors_exist(colors_cleaned, db)
    if isinstance(result, list):
        raise UnicornException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid color(s): {', '.join(result)}"
        )
    elif result is False:
        raise UnicornException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Something went wrong"
        )

    # material_cleaned = [i.strip() for i in item_data.material] if item_data.material else []
    # result = material_exist(material_cleaned, db)
    # if isinstance(result, list):
    #     raise UnicornException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         message=f"Invalid material(s): {','.join(result)}"
    #     )
    # elif result is False:
    #     raise UnicornException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         message="Something went wrong"
    #     )

    shopItemModel = models.ShopItem(**item_data.model_dump())
    shopItemModel.id = unique_id
    shopItemModel.owner_id = current_user.id
    shopItemModel.size = size_cleaned
    shopItemModel.brand = brand_cleaned.capitalize()
    shopItemModel.category = category_cleaned.capitalize()
    shopItemModel.sub_category = sub_category_cleaned.capitalize()
    shopItemModel.payment_methods = json.dumps(item_data.payment_methods)
    shopItemModel.shipping_methods = json.dumps(item_data.shipping_methods)
    shopItemModel.images = json.dumps(item_data.images)
    shopItemModel.colors = json.dumps(item_data.colors)
    shopItemModel.colors = json.dumps(colors_cleaned)
    shopItemModel.hash_tags = json.dumps(item_data.hash_tags)
    shopItemModel.material = item_data.material
    shopItemModel.condition = item_data.condition.lower() if item_data.condition else "new"

    try:
        db.add(shopItemModel)
        db.commit()
        db.refresh(shopItemModel)

        from appconfig import crud as config_crud
        # add translation
        try:
            en_title = translate_text(item_data.title, target_language="en")
            localization_title = {
                en_title: {
                    "en": en_title,
                    "fr": translate_text(item_data.title, target_language="fr"),
                    "he": translate_text(item_data.title, target_language="he")
                },
            }

            en_description = translate_text(item_data.description, target_language="en")
            localization_description = {
                en_description: {
                    "en": en_description,
                    "fr": translate_text(item_data.description, target_language="fr"),
                    "he": translate_text(item_data.description, target_language="he")
                },
            }

            config_crud.add_translation(localization_title, db)
            config_crud.add_translation(localization_description, db)

        except Exception as e:
            print("add item translation error ", e)

        return get_item_schema(shopItemModel, db)

    except IntegrityError:
        raise UnicornException(
            status_code=status.HTTP_409_CONFLICT,
            message=language_content.get('item with this id not found')
        )


def update_item(request: Request, item_id: str, item_data: schemas.AddItem, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    shopItemModel = db.query(models.ShopItem).filter_by(id=item_id).first()

    if not shopItemModel:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('item with this id not found'))

    for key, value in item_data.model_dump().items():
        setattr(shopItemModel, key, value)

    shopItemModel.payment_methods = json.dumps(item_data.payment_methods)
    shopItemModel.shipping_methods = json.dumps(item_data.shipping_methods)
    shopItemModel.images = json.dumps(item_data.images)
    shopItemModel.colors = json.dumps(item_data.colors)
    shopItemModel.hash_tags = json.dumps(item_data.hash_tags)

    db.commit()

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message=language_content.get('item updated successfully'))

    #
    # try:
    #     db.add(shopItemModel)
    #     db.commit()
    #     db.refresh(shopItemModel)
    #
    #     return shopItemModel
    #
    # except IntegrityError:
    #     raise UnicornException(status_code=status.HTTP_409_CONFLICT,
    #                            message=language_content.get('item-with-this-id-already-exists'))


def update_item_data(item_data: schemas.UpdateItem, db: Session, current_user, item_id: str):
    ItemInDb = db.query(ShopItem).filter(ShopItem.id == item_id).first()
    if not ItemInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Item doesn't exists")

    ItemInDb.price = item_data.price if item_data.price else ItemInDb.price
    ItemInDb.images = json.dumps(item_data.images) if item_data.images else ItemInDb.images
    ItemInDb.payment_methods = json.dumps(
        item_data.payment_methods if item_data.payment_methods is not None else []
    )
    ItemInDb.shipping_methods = json.dumps(
        item_data.shipping_methods) if item_data.shipping_methods else item_data.shipping_methods
    db.commit()
    return {
        "status": True,
        "message": "Item update successfully",
        "data": get_item_schema(shopItem=ItemInDb, db=db)
    }


def get_user_items(user_id: str, db: Session):
    user = db.query(User).filter_by(id=user_id).first()
    shop_items = user.shop_items

    # userItems = [shop_item_schemas(item) for item in shop_items]
    userItems = {"items": [], "rental": []}
    for item in shop_items:
        if item.category.lower() == "rental":
            userItems["rental"].append(shop_item_schemas(item))
        else:
            userItems["items"].append(shop_item_schemas(item))

    userItems['items'].reverse()
    return userItems


def get_user_deactivated_items(user_id: str, db: Session):
    user = db.query(User).filter_by(id=user_id).first()
    shop_items = user.shop_items

    userItems = [shop_item_schemas(item) for item in shop_items if item.is_active is False]
    userItems.reverse()

    return userItems


def get_item_details(query: str, request: Request, item_id: str, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    shopItemInDb = db.query(models.ShopItem).filter_by(id=item_id).first()

    if not shopItemInDb or not shopItemInDb.owner:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('item with this id not found'))

    # if shopItemInDb.owner.preferences.holiday_mode or shopItemInDb.owner.account_status is not AccountStatus.Enabled:
    #     raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
    #                            message=language_content.get('item with this id not found'))

    if query:
        query_lower = query.lower()
        if (query_lower not in shopItemInDb.category.lower()) and (
                query_lower not in shopItemInDb.sub_category.lower()):
            raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                                   message=language_content.get('item with this id not found'))

    recently_view_added = models.RecentlyViewItems(user_id=current_user.id, item_id=item_id, view_at=datetime.utcnow())
    db.add(recently_view_added)

    itemDetailsSchema = dict(get_item_schema(shopItemInDb, db))
    shopItemInDb.view_count += 1
    db.commit()
    db.refresh(recently_view_added)
    itemDetailsSchema['user_items'] = [get_item_schema(item, db) for item in shopItemInDb.owner.shop_items]
    return itemDetailsSchema


def update_shop_bundle(bundle_data: schemas.ShopBundleUpdate, current_user: User, db: Session):
    user_shop_bundle = db.query(models.Bundles).filter(models.Bundles.owner_id == current_user.id).first()

    if user_shop_bundle:
        user_shop_bundle.is_enabled = bundle_data.is_enabled
        user_shop_bundle.bundles = json.dumps(bundle_data.bundles)
        db.commit()
        raise UnicornException(status_code=status.HTTP_200_OK,
                               message="shop-bundle-updated-successfully")
    else:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="shop-bundle-not-found-for-this-user")


def get_shop_bundle(request: Request, user_id: str, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    userInDb = db.query(User).filter_by(id=user_id).first()

    if not userInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('user-with-id-not-found'))

    shop_bundle = db.query(models.Bundles).filter_by(owner_id=user_id).first()

    if shop_bundle:
        shopBundleSchema = schemas.ShopBundleInDb(
            owner_id=shop_bundle.owner_id,
            is_enabled=shop_bundle.is_enabled,
            bundles=json.loads(shop_bundle.bundles)
        )
        return shopBundleSchema

    else:
        shopModel = models.Bundles(
            owner_id=user_id,
            bundles=json.dumps([
                {"item_count": 2, "discount": 20},
                {"item_count": 3, "discount": 30},
                {"item_count": 5, "discount": 50},
            ])
        )

        db.add(shopModel)
        db.commit()
        db.refresh(shopModel)

        shopBundleSchema = schemas.ShopBundleInDb(
            owner_id=shopModel.owner_id,
            is_enabled=shopModel.is_enabled,
            bundles=json.loads(shopModel.bundles)
        )
        return shopBundleSchema


# def get_favorite_items(current_user: User, db: Session):
#     favorite_item_set = set()
#     unique_favorite_items = []
#
#     def add_unique_item(item):
#         if item.id not in favorite_item_set:
#             favorite_item_set.add(item.id)
#             unique_favorite_items.append(shop_item_schemas(item))
#
#     fav_items = (
#         db.query(models.ShopItem)
#         .select_from(favourited_items)
#         .join(models.ShopItem, favourited_items.c.item_id == models.ShopItem.id)
#         .filter(favourited_items.c.user_id == current_user.id)
#         .order_by(desc(favourited_items.c.date_created))
#         .all()
#     )
#
#     for item in fav_items:
#         add_unique_item(item)
#
#     return unique_favorite_items
def get_favorite_items(current_user: User, db: Session):
    return [get_item_schema(item, db) for item in current_user.favourited_items]


def favorite_item(request: Request, item_id: str, current_user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    itemInDb = db.query(models.ShopItem).filter_by(id=item_id).first()

    if not itemInDb or itemInDb.owner.account_status in [AccountStatus.Deleted, AccountStatus.Disabled]:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('item with this id not found'))

    if itemInDb in current_user.favourited_items:
        # current_user.favourited_items.remove(itemInDb)
        stmt = delete(favourited_items).where(favourited_items.c.item_id == item_id)
        db.execute(stmt)
        db.commit()

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('item removed from favourites'))
    else:
        db.execute(
            favourited_items.insert().values(
                user_id=current_user.id,
                item_id=itemInDb.id,
                date_created=datetime.now(timezone.utc)

            )
        )
        db.commit()

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message=language_content.get('item added to favourite'))


def get_all_brands(db: Session):
    brandsInDb = db.query(models.Brands).filter(models.Brands.enabled).all()

    all_brand = [
        schemas.BrandInDb(
            id=brand.id,
            name=brand.name,
            enabled=brand.enabled,
            featured=brand.featured,
            date_created=str(brand.date_created)
        ) for brand in brandsInDb
    ]
    return all_brand


def get_items_available_brands(db: Session):
    brandsInDb = db.query(models.Brands).filter(models.Brands.enabled).all()

    all_brand = [
        schemas.BrandInDb(
            id=brand.id,
            name=brand.name,
            enabled=brand.enabled,
            featured=brand.featured,
            date_created=str(brand.date_created)
        ) for brand in brandsInDb if db.query(models.ShopItem).filter(models.ShopItem.brand == brand.name).count() >= 10
    ]
    return all_brand


def get_categories(db: Session):
    sort_column = getattr(models.Category, 'date_created')
    sort_order = asc(sort_column)
    categoryInDb = db.query(models.Category).filter(models.Category.enabled).order_by(sort_order).all()

    return [schemas.CategoryInDb.model_validate(category) for category in categoryInDb]


def get_categories_all(db: Session):
    sort_column = getattr(models.Category, 'date_created')
    sort_order = asc(sort_column)
    categoryInDb = db.query(models.Category).filter(models.Category.enabled).order_by(sort_order).all()

    categories_with_items = []
    for category in categoryInDb:
        if db.query(models.ShopItem).filter_by(category=category.name).first():
            categories_with_items.append(category)

    categories_with_items.insert(0, models.Category(id='all', translation_key='all', featured=False, name='All',
                                                    priority=0,
                                                    enabled=True, date_created=datetime.utcnow()))

    return [schemas.CategoryInDb.model_validate(category) for category in categories_with_items]


def add_category(category_data: schemas.CategoryBase, db: Session):
    unique_id = str(uuid4())

    categoryDataDict = category_data.model_dump()
    categoryDataDict['id'] = unique_id
    categoryModel = models.Category(**categoryDataDict)

    try:
        db.add(categoryModel)
        db.commit()
        db.refresh(categoryModel)

        return schemas.CategoryInDb.model_validate(categoryModel)

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="Category with this name already exists")


def add_subcategory(subcategory: schemas.SubCategoryBase, db: Session):
    unique_id = str(uuid4())
    categoryInDb = db.query(models.Category).filter_by(id=subcategory.category_id).first()

    if not categoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found")

    subCategoryDataDict = subcategory.model_dump()
    subCategoryDataDict['id'] = unique_id

    subCategoryModel = models.SubCategory(**subCategoryDataDict)

    try:
        db.add(subCategoryModel)
        db.commit()
        db.refresh(subCategoryModel)

        return schemas.SubCategoryInDb.model_validate(subCategoryModel)

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="Sub Category with this name already exists")

    # sub_categories = []
    #
    # for category in subCategoryInDb:
    #     if category_id == 'all':
    #         sub_categories.append(
    #             schemas.SubCategoryInDb(
    #                 id=category.id,
    #                 name=category.name,
    #                 parent_category=category.parent_category.name,
    #                 featured=category.featured,
    #                 date_created=str(category.date_created)
    #             )
    #         )
    #     else:
    #         if category.parent_category.id == category_id:
    #             sub_categories.append(
    #                 schemas.SubCategoryInDb(
    #                     id=category.id,
    #                     name=category.name,
    #                     parent_category=category.parent_category.name,
    #                     featured=category.featured,
    #                     sub_categories=json.loads(category.sub_categories),
    #                     date_created=str(category.date_created)
    #                 )
    #             )
    #
    # return sub_categories


def get_subcategories(category_id: str, db: Session):
    print("jj")
    categoryInDb = db.query(models.Category).filter_by(id=category_id).first()

    if not categoryInDb and category_id != 'all':
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found")

    if category_id == 'all':
        allSubCategories = db.query(models.SubCategory).all()
    else:
        allSubCategories = categoryInDb.sub_categories

    return [schemas.SubCategoryInDb.model_validate(subCategory) for subCategory in allSubCategories]


def get_subcategories_all(category_id: str, db: Session):
    categoryInDb = db.query(models.Category).filter_by(id=category_id).first()
    if not categoryInDb and category_id != 'all':
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found")
    subcategories_with_items = []
    if category_id == 'all':
        allSubCategories = db.query(models.SubCategory).all()
    else:
        allSubCategories = categoryInDb.sub_categories
    for subCategory in allSubCategories:
        if db.query(models.ShopItem).filter_by(sub_category=subCategory.name).first():
            subcategories_with_items.append(subCategory)

    # subcategories_with_items.insert(0, schemas.SubCategoryInDb(id='all', name='All', enabled=True, date_created=''))

    return [schemas.SubCategoryInDb.model_validate(subCategory) for subCategory in subcategories_with_items]


def get_subcategory_items(sub_category_id: str, db: Session):
    subcategoryInDb = db.query(models.SubCategory).filter_by(id=sub_category_id).first()
    if not subcategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Subcategory with this id not found")

    return [schemas.SubCategoryItemInDb.model_validate(item) for item in subcategoryInDb.category_items]


def get_sub_sub_subcategory_items(sub_category_id: str, db: Session):
    subcategoryInDb = db.query(models.SubCategoryItems).filter_by(id=sub_category_id).first()
    if not subcategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Subcategory with this id not found")

    return [schemas.SubCategoryItemInDb.model_validate(item) for item in subcategoryInDb.sub_sub_category]


def get_sub_sub_subcategory_level_items(sub_category_id: str, db: Session):
    subcategoryInDb = db.query(models.SubSubCategoryItems).filter_by(id=sub_category_id).first()
    if not subcategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Subcategory with this id not found")

    return [schemas.SubCategoryItemInDb.model_validate(item) for item in subcategoryInDb.sub_sub_category_level]


def get_subcategory_items_all(sub_category_id: str, db: Session):
    subcategoryInDb = db.query(models.SubCategory).filter_by(id=sub_category_id).first()
    if not subcategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Subcategory with this id not found")

    subcategory_items_with_products = []
    for item in subcategoryInDb.category_items:
        if db.query(models.ShopItem).filter_by(type=item.name).first():
            subcategory_items_with_products.append(item)

    return [schemas.SubCategoryItemInDb.model_validate(item) for item in subcategory_items_with_products]


def add_subcategory_item(subcategoryItemData: schemas.SubCategoryItemBase, db: Session):
    unique_id = str(uuid4())

    subcategoryItemDataDict = subcategoryItemData.model_dump()
    subcategoryItemDataDict['id'] = unique_id
    subCategoryItemModel = models.SubCategoryItems(**subcategoryItemDataDict)

    try:
        db.add(subCategoryItemModel)
        db.commit()
        db.refresh(subCategoryItemModel)

        return schemas.SubCategoryItemInDb.model_validate(subCategoryItemModel)

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="Subcategory with this name already exists")


def get_sizes(db: Session):
    sizesInDb = db.query(models.Sizes).all()
    return [schemas.SizeInDb.model_validate(size) for size in sizesInDb]


def add_size(size: str, db: Session):
    sizeModel = models.Sizes(
        id=str(uuid4()),
        size=size
    )

    try:
        db.add(sizeModel)
        db.commit()
        db.refresh(sizeModel)

        return schemas.SizeInDb.model_validate(sizeModel)

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="This size name already exists")
    # sizesInDb = db.query(models.Sizes).all()
    #
    # all_sizes = [
    #     schemas.SizeInDb(
    #         id=size.id,
    #         size=size.size,
    #         date_created=str(size.date_created)
    #     ) for size in sizesInDb
    # ]
    #
    # return all_sizes


def get_colors(db: Session):
    colorsInDb = db.query(models.Colors).all()
    return [color for color in colorsInDb]


def extract_multiple_items(allItemsInDb, db: Session):
    return [
        get_item_schema(shopItem=item, db=db) for item in allItemsInDb if
        not item.owner.preferences.holiday_mode and item.owner.account_status is AccountStatus.Enabled
    ]


# def get_popular_items(category: str, user: User, db: Session):  # new change by me
#     data = []
# boosted_subscription = (
#     db.query(UserSubscription)
#     .join(UserSubscription.plan)
#     .filter(
#         UserSubscription.expire_on >= datetime.utcnow(),
#         SubscriptionPlan.subscription_type == SubscriptionTypeEnum.BOOSTED_VISIBILITY
#     )
# ).all()
# for boosted_sub in boosted_subscription:
#     data += [
#         get_item_schema(shopItem=item, db=db) for item in boosted_sub.user.shop_items if
#         not item.owner.preferences.holiday_mode and item.owner.account_status is AccountStatus.Enabled
#         and (True if category == "all" else (item.category == category or item.category == category.lower()))
#     ]

# second_hand_most_favorite_items = db.query(models.ShopItem).filter(
#     models.ShopItem.favorited_by.any(ShopItem.condition == models.ConditionTypeEnum.USED),
#
# ).distinct().all()
# existing_ids = [item.id for item in data]
# result = [
#              get_item_schema(shopItem=item, db=db) for item in second_hand_most_favorite_items if
#              not item.owner.preferences.holiday_mode and item.owner.account_status is AccountStatus.Enabled
#              and (True if category == "all" else (item.category == category or item.category == category.lower()))
#              and item.id not in existing_ids
#          ] + data
#
# # get_item_schema(
# #         shopItem=item,
# #         db=db
# #     ) not in data and
# return result


def get_popular_items(category: str, db: Session, language_code, user: Optional[User] = None):  # old code
    allItemsInDb = sold_item_visibility(db.query(models.ShopItem)).filter_by(is_sold=False).all()
    boostedItemsInDb = db.query(models.ShopItem).filter_by(is_boosted=True).all()

    allItemsByCat = [schemas.ShopItem.model_validate(item) for item in allItemsInDb if
                     not item.owner.preferences.holiday_mode and item.owner.account_status is AccountStatus.Enabled]

    boostedItems = [schemas.ShopItem.model_validate(item) for item in boostedItemsInDb if
                    not item.owner.preferences.holiday_mode and item.owner.account_status is AccountStatus.Enabled]

    random.shuffle(boostedItems)
    key = operator.itemgetter("view_count")

    items = sorted(
        jsonable_encoder(allItemsByCat) if category == "all" else
        jsonable_encoder([item for item in allItemsByCat if item.category == category]),
        key=key,
        reverse=True
    )
    # if language_code != "en":
    #     lang_map = get_lang_content(language_code)
    #
    #     for item in items:
    #         title = item.get("title", "")
    #         description = item.get("description", "")
    #
    #         if title:
    #             if title in lang_map:
    #                 item["title"] = lang_map[title]
    #             else:
    #                 item["title"] = translate_text(title, target_language=language_code, source_language="en")
    #
    #         if description:
    #             if description in lang_map:
    #                 item["description"] = lang_map[description]
    #             else:
    #                 item["description"] = translate_text(description, target_language=language_code,
    #                                                      source_language="en")

    items = boostedItems + items
    return items


# def get_all_sellers(current_user: User, db: Session):
#     if not is_user_subscription_active(db=db, user_id=current_user.id, subscription_type="featured-dressing"):
#         raise UnicornException(status_code=status.HTTP_400_BAD_REQUEST,
#                                message=f"Your featured dressing plan is not active. please choose plan to get product")
#
#     sellers_details = (db.query(User).join(User.subscriptions)
#                        .join(UserSubscription.plan)
#                        .filter(SubscriptionPlan.subscription_type == SubscriptionTypeEnum.SELLER).all())
#
#     response = []
#     for seller in sellers_details:
#         items = [schemas.ShopItem.model_validate(item) for item in seller.shop_items]
#         # print("items", items)
#
#         seller_data = {
#             "id": seller.id,
#             "name": seller.profile.fullname,
#             "items": items
#         }
#         response.append(seller_data)
#     return response


def get_explore_list(current_user: User, db: Session):
    exploreItemList = []
    # usersStatuses = []
    userFollowingList = current_user.following
    userFollowersList = current_user.followed_by

    key = operator.itemgetter("date_created")

    allUsers = [*userFollowingList, *userFollowersList]
    for user in allUsers:
        userShopItems = sold_item_visibility(db.query(models.ShopItem)).filter_by(owner_id=user.id).all()

        for shopItemInDb in userShopItems:
            exploreItemList.append(
                get_item_schema(shopItemInDb, db)
            )

    return sorted(jsonable_encoder(exploreItemList), key=key)


def get_posted_recently_items(category: str, db: Session, current_user: Optional[User] = None):
    seven_days_ago = datetime.now() - timedelta(days=7)
    # allItemsInDb = db.query(models.ShopItem).filter_by(is_sold=False).all()
    query = db.query(ShopItem)
    query = sold_item_visibility(query)
    items = query.all()

    allItemsByCat = [get_item_schema(item, db) for item in items if
                     not item.owner.preferences.holiday_mode and item.owner.account_status == AccountStatus.Enabled and item.date_created >= seven_days_ago]

    key = operator.itemgetter("date_created")

    if category.lower() == "all":
        return sorted(jsonable_encoder(allItemsByCat), key=key, reverse=True)

    return sorted(jsonable_encoder([item for item in allItemsByCat if item.category.lower() == category.lower()]),
                  key=key, reverse=True)


def shop_item_schemas(shop_items):
    shopItemSchema = schemas.ShopItem.model_validate(shop_items)

    return shopItemSchema


def buy_item_create_payment_session(sale_data: schemas.BuyItem,
                                    user: User, db: Session):
    shopItemInDb = db.query(models.ShopItem).filter(
        models.ShopItem.id == sale_data.item_id,
        models.ShopItem.category != "Rental",
    ).first()

    if not shopItemInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=f"Item not found invalid id")
    elif shopItemInDb.is_sold is True:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=f"Sorry your select item may be already sold, Please try again.")

    elif shopItemInDb.is_active is False:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=f"Sorry your select item is not available yet, Please try another.")

    payment_request = payment_schema.PaymentRequest(
        price=shopItemInDb.price,
        description=shopItemInDb.description,
        shop_item_id=shopItemInDb.id
    )
    return payment_crud.paypal_create_payment_session(
        data=payment_request,
        db=db,
        current_user=user,
        sale_data=sale_data.model_dump()
    )


def create_buy_item(background_tasks: BackgroundTasks, sale_data: schemas.BuyItem, user: User,
                    db: Session):
    shopItemInDb = db.query(models.ShopItem).filter(models.ShopItem.id == sale_data['item_id']).first()

    unique_id = str(uuid4())
    saleItemModel = models.Sales(
        id=unique_id,
        item_id=sale_data['item_id'],
        delivery_method=sale_data['delivery_method'],
        delivery_details=sale_data['delivery_details'],
        buyer_id=user.id,
        final_price=sale_data['final_price'],
    )

    # update item
    shopItemInDb.is_sold = True

    db.add(saleItemModel)
    db.commit()
    db.refresh(saleItemModel)

    notificationCreateSchema = notification_schemas.NotificationBase(
        receiver_id=shopItemInDb.owner_id,
        type=notification_schemas.NotificationType.ItemSale,
    )

    notificationData = notification_crud.get_notification_data(notificationCreateSchema.type,
                                                               {"sender_name": user.profile.fullname})

    background_tasks.add_task(notification_crud.send_local_notification, notificationCreateSchema,
                              db,
                              user.id)

    background_tasks.add_task(notification_crud.send_push_notification, notificationCreateSchema,
                              notificationData.get('headings'), notificationData.get('contents'), db)

    print("--- buy item created successfully ----")


def buy_item(request: Request, sale_data: schemas.BuyItem, user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    sales_records = []
    unavailable_items = []

    for item_id in sale_data.item_id:
        shop_item = db.query(ShopItem).filter_by(id=item_id).first()
        if shop_item.owner.preferences and shop_item.owner.preferences.holiday_mode == True:
            return {'status': False, 'message': 'Seller is on holiday mode'}
        if shop_item.is_sold == True:
            unavailable_items.append(item_id)

    if unavailable_items:
        return {"status": False, "message": "Currently this item is not available"}

    payment_data = payment_crud.get_payment_url(user=user, shop_items_ids=sale_data.item_id, db=db,
                                                final_price=sale_data.final_price)
    apppay_url = payment_data.get("payment_url")

    order_id = payment_data.get("order_id")
    payment_record = db.query(AllPayPayment).filter_by(order_id=order_id).first()

    for item_id in sale_data.item_id:
        sale = Sales(
            id=str(uuid.uuid4()),
            item_id=item_id,
            buyer_id=user.id,
            final_price=sale_data.final_price,
            sale_status=SaleStatus.NotShipped,
            table_payment_id=payment_record.id,
            delivery_method=sale_data.delivery_method,
            delivery_details=sale_data.delivery_details,
            is_protected_purchase=(sale_data.delivery_method != "meeting point")
        )

        db.add(sale)
        sales_records.append(sale)
    db.commit()
    return {"message": language_content.get("payment url create successfully"), "status": True,
            "payment_url": apppay_url}


def mark_as_sold(request: Request, item_id: str, user: User, db: Session):
    lang = request.headers.get('X-language', 'en')
    language_content = get_lang_content(lang)

    itemInDb = db.query(models.ShopItem).filter(models.ShopItem.id == item_id).first()

    if not itemInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message=language_content.get('item-not-found'))

    if itemInDb.owner_id != user.id:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message=language_content.get('not authorized to modify item'))

    if itemInDb.is_sold:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message=language_content.get('item sold already'))

    itemInDb.is_sold = True
    db.commit()

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message=language_content.get('item marked as sold successfully'))


def get_shop_sales(user: User, db: Session):
    salesInDb = db.query(models.Sales).all()
    # print("SalesInDb:", salesInDb)
    # print("Current User:", user.id)
    allPurchasedItem = []

    for sale in salesInDb:
        # print("Sale:", sale.id, "ShopItem:", sale.shop_item, "Owner:", getattr(sale.shop_item, 'owner_id', None))
        if sale.shop_item.owner_id == user.id:
            # print("enter")
            salesSchema = schemas.SaleItemsInDb.model_validate(salesInDb[0])
            salesSchema.item_image = json.loads(sale.shop_item.images)[0]
            salesSchema.item_title = sale.shop_item.title
            salesSchema.seller_id = sale.shop_item.owner.id
            salesSchema.seller_username = sale.shop_item.owner.profile.username
            salesSchema.buyer_username = sale.buyer.profile.username
            salesSchema.item_brand = sale.shop_item.brand
            salesSchema.item_subCategory = sale.shop_item.sub_category

            allPurchasedItem.append(salesSchema)

    allPurchasedItem.reverse()

    return allPurchasedItem


def get_purchased_item(user: User, db: Session):
    salesInDb = db.query(models.Sales).all()

    allPurchasedItem = []

    for sale in salesInDb:
        if sale.buyer_id == user.id:
            salesSchema = schemas.SaleItemsInDb.model_validate(salesInDb[0])
            salesSchema.item_image = json.loads(sale.shop_item.images)[0]
            salesSchema.item_title = sale.shop_item.title
            salesSchema.seller_id = sale.shop_item.owner.id
            salesSchema.seller_username = sale.shop_item.owner.profile.username
            salesSchema.buyer_username = sale.buyer.profile.username
            salesSchema.item_brand = sale.shop_item.brand
            salesSchema.item_subCategory = sale.shop_item.sub_category
            allPurchasedItem.append(salesSchema)

    allPurchasedItem.reverse()
    return allPurchasedItem


def update_shop_sale(background_tasks: BackgroundTasks, sale_id: str, sale_status: schemas.SaleStatus, user: User,
                     db: Session):
    salesInDb = db.query(models.Sales).filter(models.Sales.id == sale_id).first()
    item_owner_id = salesInDb.shop_item.owner_id
    if not salesInDb:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="Sale with this id not found")

    salesInDb.sale_status = sale_status
    db.commit()

    if sale_status == schemas.SaleStatus.Completed:
        notification_crud.notify_sales_status_change(background_tasks, db, sale_status,
                                                     sale_id, item_owner_id, "Admin")
    else:
        notification_crud.notify_sales_status_change(background_tasks, db, sale_status,
                                                     sale_id, salesInDb.buyer_id, item_owner_id)

    return {"message": "Sale status updated successfully", "status": True}


def delete_shipped_sale(sale_id: str, user: User, db: Session):
    salesInDb = db.query(models.Sales).filter(models.Sales.id == sale_id).first()

    if salesInDb:
        db.delete(salesInDb)
        db.commit()
        raise UnicornException(status_code=status.HTTP_200_OK,
                               message="Shipped sale deleted successfully")

    raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                           message="Sale with this id not found")


def get_item_schema(shopItem: models.ShopItem, db: Session):
    allFavouriteItems = db.query(auth_models.favourited_items).filter_by(item_id=shopItem.id).all()

    itemDetailsSchema = schemas.ShopItemDetails.model_validate(shopItem)

    ownerRatingInDb = db.query(UserRatings).filter_by(rated_user_id=shopItem.owner.id).all()
    allUserRating = [rating.value for rating in ownerRatingInDb]

    itemOwnerSchema = schemas.ItemOwner.model_validate(shopItem.owner)
    itemOwnerSchema.average_rating = float(calculate_average(allUserRating))
    itemOwnerSchema.ratings_count = len(allUserRating)
    itemOwnerSchema.fullname = shopItem.owner.profile.fullname
    itemOwnerSchema.address = shopItem.owner.profile.address
    itemOwnerSchema.country = shopItem.owner.profile.country.name
    itemOwnerSchema.username = shopItem.owner.profile.username
    itemOwnerSchema.profile_pic = shopItem.owner.profile.profile_pic
    itemOwnerSchema.profile_pic = itemOwnerSchema.profile_picture
    itemDetailsSchema.interested_members = len([fav for fav in allFavouriteItems])
    itemDetailsSchema.owner = itemOwnerSchema
    return itemDetailsSchema


def recently_viewed_schema(user, db, current_user_id):
    rec_view = db.query(models.RecentlyViewed).filter_by(user_id=user.id).first()
    RecentlyViewSchema = schemas.ItemBase.model_validate(user)


def get_recently_viewed_schema(db: Session, user_id: str):
    recently_viewed_items = (sold_item_visibility(
        db.query(models.RecentlyViewItems, models.ShopItem)
        .join(models.ShopItem, models.RecentlyViewItems.item_id == models.ShopItem.id))
                             .filter(models.RecentlyViewItems.user_id == user_id)
                             .distinct(models.RecentlyViewItems.item_id)
                             .order_by(models.RecentlyViewItems.item_id, models.RecentlyViewItems.view_at.desc())
                             .all()
                             )
    if not recently_viewed_items:
        return []
    result = []
    for viewed, shop_item in recently_viewed_items:
        shop_item_schema = schemas.ShopItemDetails.model_validate(shop_item)
        recently_viewed_schema = schemas.RecentlyViewItemsSchema(
            id=viewed.id,
            item=shop_item_schema,
            view_at=viewed.view_at
        )
        result.append(recently_viewed_schema)
    return result


def featured_dressing_item(db: Session, current_user: User):
    from subscription.models import UserSubscription, SubscriptionTypeEnum
    from datetime import datetime

    active_subs = db.query(UserSubscription).filter(
        UserSubscription.subscription_type == SubscriptionTypeEnum.FEATURED_DRESSING,
        UserSubscription.expire_on >= datetime.utcnow()
    ).all()

    user_ids = [sub.user_id for sub in active_subs]

    featured_users = db.query(User).filter(User.id.in_(user_ids)).all()

    response = []
    for seller in featured_users:
        all_items = seller.shop_items
        items = [
            get_item_schema(item, db)
            for item in all_items
            if item.is_active and not item.is_sold
        ]

        seller_data = {
            "id": seller.id,
            "fullname": seller.profile.fullname,
            "username": seller.profile.username,
            "nickname": seller.profile.nickname,
            "address": seller.profile.address,
            "country": seller.profile.country.name,
            "profile_pic": seller.profile.profile_pic if seller.profile else "",
            "account_status": seller.account_status,
            "items": items,
        }
        response.append(seller_data)

    return response


# def featured_dressing_item(current_user: User, db: Session):
#     # if not is_user_subscription_active(db=db, user_id=current_user.id, subscription_type="featured-dressing"):
#     #     raise UnicornException(status_code=status.HTTP_400_BAD_REQUEST,
#     #                            message=f"Your featured dressing plan is not active. please choose plan to get product")
#
#     # sellers_details = (db.query(User).join(User.subscriptions).join(UserSubscription.plan).all())
#     sellers_details = (db.query(User).limit(10).all())
#     # sellers_details = (db.query(User).join(User.subscriptions).join(UserSubscription.plan).filter(UserSubscription.plan.subscription_type
#     # ==     SubscriptionTypeEnum.SELLER).all(
#     # .filter(SubscriptionPlan.subscription_type == SubscriptionTypeEnum.SELLER)
#     # print(sellers_details)
#
#     response = []
#     for seller in sellers_details:
#         items = [get_item_schema(item, db) for item in seller.shop_items]
#         if not items:
#             continue
#         itemOwnerSchema = schemas.ItemOwner.model_validate(seller)
#         itemOwnerSchema.fullname = seller.profile.fullname
#         seller_data = {
#             "id": seller.id,
#             "fullname": seller.profile.fullname,
#             "username": seller.profile.username,
#             "address": seller.profile.address,
#             "country": seller.profile.country.name,
#             "profile_pic": itemOwnerSchema.profile_picture,
#             "nickname": seller.profile.nickname,
#             "account_status": seller.account_status,
#             "items": items
#         }
#         response.append(seller_data)
#     return response


def shoes_listing_detail(db: Session):
    # filters = ShopItem.size.ilike(f"%{size}%")
    shoes_detail = sold_item_visibility(
        db.query(ShopItem)
        .filter(or_(
            ShopItem.category.ilike("shoes"),
            ShopItem.category.ilike("shoe"),
            ShopItem.sub_category.ilike("shoes"),
            ShopItem.sub_category.ilike("shoe"),
            ShopItem.type.ilike(f"%shoes%"),
            ShopItem.type.ilike(f"%shoe%"),
        ))).all()
    return [get_item_schema(shopItem=item, db=db) for item in shoes_detail]


def category_suggestion(db: Session):
    data = []
    Categories = db.query(models.Category.name).filter(
        models.Category.enabled.is_(True)
    ).all()

    for category in Categories:
        ItemsInDb = db.query(ShopItem).filter(
            ShopItem.category == category.name
        ).distinct().all()
        items = [schemas.ShopItem.model_validate(item) for item in ItemsInDb]
        if len(items) > 0:
            shuffled_shop_items = random.sample(items, k=len(items))
            data.append(
                {
                    "title": category.name,
                    "items": shuffled_shop_items
                }
            )

    return random.sample(data, k=len(data))


def item_hide(user: User, db: Session, item_id: str):
    ItemInDb = db.query(ShopItem).filter(ShopItem.id == item_id, ShopItem.owner_id == user.id).first()
    if not ItemInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message='item not found')

    ItemInDb.is_active = True if ItemInDb.is_active is False else False
    db.commit()
    return {
        "status": "ok",
        "message": f"item {'deactivate' if ItemInDb.is_active is False else 'activate'} successfully."
    }


def get_all_items_materials(db):
    materials = db.query(models.ItemMaterial).all()
    return materials


def shoes_sizes(db):
    shoesSizes = db.query(models.ShoeSizes).all()

    grouped = defaultdict(list)
    for shoe in shoesSizes:
        grouped[shoe.type].append(schemas.ShoeSizeSchema(id=shoe.id, size=shoe.size))

    return grouped


def create_rental(rental: schemas.RentalCreate, db: Session, user: User):
    now = datetime.utcnow()
    if rental.start_date < now or rental.end_date < now:
        raise UnicornException(status_code=400, message="Rental dates cannot be in the past")

    if rental.end_date <= rental.start_date:
        raise UnicornException(status_code=400, message="End date must be after start date")

    item = db.query(models.ShopItem).filter(
        models.ShopItem.id == rental.item_id,
        models.ShopItem.category == "Rental"
    ).first()

    if not item:
        raise UnicornException(status_code=404, message="Item not found")

    if item.is_sold is True or item.is_active is False:
        raise UnicornException(status_code=400, message="Item not available for rent")

    # Check for overlapping rentals
    overlapping_rental = db.query(models.Rental).filter(
        models.Rental.item_id == rental.item_id,
        models.Rental.is_active == True,
        ~(
                (models.Rental.end_date <= rental.start_date) |
                (models.Rental.start_date >= rental.end_date)
        )
    ).first()

    if overlapping_rental:
        raise UnicornException(status_code=400, message="Item is already rented for the selected date")

    duration_days = (rental.end_date - rental.start_date).days
    total_cost = item.price * duration_days

    # Create rental
    db_rental = models.Rental(
        item_id=rental.item_id,
        renter_id=user.id,
        start_date=rental.start_date,
        end_date=rental.end_date,
        total_cost=total_cost,
        is_active=True
    )
    db.add(db_rental)
    db.commit()
    db.refresh(db_rental)
    return db_rental


def get_report_reasons(db: Session):
    return db.query(ReportReason).order_by(ReportReason.created_at.desc()).all()


def create_report_reason(db: Session, data: ReportReasonBase):
    reason = ReportReason(
        id=str(uuid4()),
        title=data.title
    )
    db.add(reason)
    db.commit()
    db.refresh(reason)
    return reason


def create_item_report(db: Session, user_id: str, payload: ItemReportCreate):
    item = db.query(ShopItem).filter(ShopItem.id == payload.item_id).first()
    if not item:
        raise UnicornException(status_code=404, message="Item not found")

    existing = db.query(ItemReport).filter(ItemReport.user_id == user_id,
                                           ItemReport.item_id == payload.item_id).first()
    if existing:
        raise UnicornException(status_code=400, message="Item already reported by this user")

    has_reasons = payload.reason_ids and len(payload.reason_ids) > 0
    has_other = payload.other and payload.other.strip() != ""

    if not has_reasons and not has_other:
        raise UnicornException(status_code=400, message="Either select reasons or provide other details")

    if has_reasons:
        reasons = db.query(ReportReason).filter(
            ReportReason.id.in_(payload.reason_ids)
        ).all()
        if len(reasons) != len(payload.reason_ids):
            raise UnicornException(status_code=400, message="Invalid report reason")

    report = ItemReport(
        id=str(uuid4()),
        user_id=user_id,
        item_id=payload.item_id,
        other=payload.other or ""
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    if has_reasons:
        for reason_id in payload.reason_ids:
            link = ItemReportReason(
                id=str(uuid4()),
                report_id=report.id,
                reason_id=reason_id
            )
            db.add(link)
        db.commit()

    return report
