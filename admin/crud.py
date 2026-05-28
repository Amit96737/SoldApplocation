import uuid, json
from uuid import uuid4

import cloudinary
import emoji
from cloudinary.uploader import upload
from fastapi.encoders import jsonable_encoder
from jose import jwt
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
import re
from appconfig import crud as config_crud
from auth import models as auth_models, schemas as auth_schemas
from constants import SECRET_KEY, ALGORITHM
from exception import UnicornException
from profile import crud as profile_crud, models as profile_models
from shop import models as shop_models, schemas as shop_schemas
from . import models, schemas
from auth.crud import get_password_hash
from admin.models import Administrator
from datetime import datetime, timedelta
from sqlalchemy import func
from forum import models as forum_model
from fastapi import HTTPException
from sqlalchemy import case, cast, Float
from sqlalchemy import or_


templates = Jinja2Templates(directory="templates")


def get_users_list(request, db, page: int, limit: int):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    offset = (page - 1) * limit
    search_q = request.query_params.get("q")

    user_query = db.query(auth_models.User).filter(
        auth_models.User.account_status != auth_schemas.AccountStatus.Deleted
    )

    if search_q:
        user_query = user_query.filter(
            or_(
                auth_models.User.email_address.ilike(f"%{search_q}%")
            )
        )
    total_users = user_query.count()

    usersInDb = (
        user_query
        .order_by(auth_models.User.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    usersList = [
        jsonable_encoder(profile_crud.get_user_profile_schema(user, db))
        for user in usersInDb
    ]

    return templates.TemplateResponse(
        "/pages/users.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_message": flash_message,
            "users": usersList,
            "active_page": "users-page",
            "total": total_users,
            "page": page,
            "limit": limit,
        })


async def edit_user_account(request: Request, user_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    userProfileInDb = db.query(profile_models.Profile).filter_by(id=user_id).first()

    if not userProfileInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="User with this id not found.")

    formData = await request.form()

    if formData.get('profile_picture').size > 0:
        uploaded_image_url = cloudinary.uploader.upload(formData.get('profile_picture').file,
                                                        folder=f"Sold/Users/{userProfileInDb.id}")

        userProfileInDb.profile_pic = uploaded_image_url

    if formData.get('account_status') is not None:
        account_status = formData.get('account_status')
        userProfileInDb.user.account_status = account_status

    for key, value in formData.items():
        setattr(userProfileInDb, key, value)

    db.commit()

    return True

def get_shop_category(request: Request, db: Session, page: int, limit: int):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    offset = (page - 1) * limit
    search_q = request.query_params.get("q")
    query = db.query(shop_models.Category)

    if search_q:
        query = query.filter(
            or_(
                shop_models.Category.name.ilike(f"%{search_q}%"),
                shop_models.Category.id.ilike(f"%{search_q}%")
            )
        )
    total_categories = query.count()

    categoryInDb = (
        query.order_by(asc(shop_models.Category.priority))
        .offset(offset)
        .limit(limit)
        .all()
    )
    shop_category_data = []
    for category in categoryInDb:
        category_data = jsonable_encoder(category)
        category_translation = config_crud.get_localization(category.translation_key, db)
        category_data['translations'] = category_translation
        shop_category_data.append(category_data)

    return templates.TemplateResponse(
        "/pages/shop/category-page.html",
        {
            "request": request,
            "current_user": current_user,
            "flash_message": flash_message,
            "categories": shop_category_data,
            "total": total_categories,
            "page": page,
            "limit": limit,
            "active_page": "shop-category-page",
        },
    )

def edit_category(request: Request, data: dict, category_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    categoryInDb = db.query(shop_models.Category).filter_by(id=category_id).first()

    if not categoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found.")

    if data.get('name'):
        title = data['name']

        localization_data = {
            categoryInDb.translation_key: {
                "en": title.get('en', ''),
                "fr": title.get('fr', ''),
                "he": title.get('he', '')
            },
        }

        config_crud.add_translation(localization_data, db)

        categoryInDb.name = emoji.replace_emoji(data['name'].get('en', ''), replace='').lstrip()

        data.pop('name')

    for key, value in data.items():
        setattr(categoryInDb, key, value)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop category updated successfully."}

    return True


def add_category(request: Request, category_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    title = category_data['title']

    if not title.get('en') or not title.get('en').strip():
        request.session["flash_message"] = {
            "type": "error",
            "message": "Title is required"
        }
        return False

    category_trans_key = title.get('en').lower()

    localization_data = {
        category_trans_key: {
            "en": title.get('en', ''),
            "fr": title.get('fr', ''),
            "he": title.get('he', '')
        },
    }

    config_crud.add_translation(localization_data, db)
    unique_id = str(uuid4())

    categoryModel = shop_models.Category(
        id=unique_id,
        name=title.get('en').capitalize(),
        translation_key=category_trans_key,
    )

    db.add(categoryModel)
    db.commit()
    db.refresh(categoryModel)

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop category added successfully."}

    return True


def delete_category(request: Request, category_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    categoryInDb = db.query(shop_models.Category).filter_by(id=category_id).first()

    if not categoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found.")

    db.delete(categoryInDb)
    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Category deleted successfully."}

    return True

def get_shop_sub_category(request: Request, db: Session, page: int, limit: int):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    search_q = request.query_params.get("q")
    offset = (page - 1) * limit
    categoryInDb = db.query(shop_models.Category).all()

    subCategoryQuery = db.query(shop_models.SubCategory).join(
        shop_models.Category,
        shop_models.SubCategory.category_id == shop_models.Category.id
    )

    if search_q:
        subCategoryQuery = subCategoryQuery.filter(
            or_(
                shop_models.SubCategory.name.ilike(f"%{search_q}%"),
                shop_models.Category.name.ilike(f"%{search_q}%")
            )
        )

    total_sub_categories = subCategoryQuery.count()
    subCategoryInDb = (
        subCategoryQuery
        .order_by(shop_models.SubCategory.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    shop_sub_category_data = []
    for subcategory in subCategoryInDb:
        subCategorySchema = shop_schemas.SubCategoryInDb.model_validate(subcategory)
        subCategorySchema.parent_category_name = subcategory.parent_category.name
        subcategory_data = jsonable_encoder(subCategorySchema)
        category_translation = config_crud.get_localization(subcategory.translation_key, db)
        subcategory_data['translations'] = category_translation
        shop_sub_category_data.append(subcategory_data)

    return templates.TemplateResponse("/pages/shop/subcategory-page.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "categoryInDb": [jsonable_encoder(category) for category in categoryInDb],
                                       "flash_message": flash_message,
                                       "sub_categories": shop_sub_category_data,
                                       "total": total_sub_categories,
                                       "page": page,
                                       "limit": limit,
                                       "active_page": "subcategory-page"})

def get_shop_sub_category_items(request: Request, sub_category_id: str, db: Session):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    subCategoryInDb = db.query(shop_models.SubCategory).filter_by(id=sub_category_id).first()

    if not subCategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found.")

    shop_sub_category_item_data = []
    for item in subCategoryInDb.category_items:
        subCategoryItem_data = jsonable_encoder(item)
        category_translation = config_crud.get_localization(item.translation_key, db)
        subCategoryItem_data['translations'] = category_translation
        shop_sub_category_item_data.append(subCategoryItem_data)

    return templates.TemplateResponse("/pages/shop/subcategory-items-page.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "flash_message": flash_message,
                                       "sub_category": subCategoryInDb,
                                       "sub_categories_items": shop_sub_category_item_data,
                                       "active_page": "subcategory-page"})

def get_shop_sub_sub_category_items(request: Request, sub_sub_category_id: str, db: Session):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    subCategoryInDb = db.query(shop_models.SubCategoryItems).filter_by(id=sub_sub_category_id).first()

    if not subCategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Sub category with this id not found.")

    shop_sub_category_item_data = []
    for item in subCategoryInDb.sub_sub_category:
        subCategoryItem_data = jsonable_encoder(item)
        category_translation = config_crud.get_localization(item.translation_key, db)
        subCategoryItem_data['translations'] = category_translation
        shop_sub_category_item_data.append(subCategoryItem_data)

    return templates.TemplateResponse("/pages/shop/sub-subcategory-items-page.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "flash_message": flash_message,
                                       "sub_category": subCategoryInDb,
                                       "sub_categories_items": shop_sub_category_item_data,
                                       "active_page": "subcategory-page"})


def get_shop_sub_sub_category_level_items(request: Request, sub_sub_category_id: str, db: Session):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    subCategoryInDb = db.query(shop_models.SubSubCategoryItems).filter_by(id=sub_sub_category_id).first()

    if not subCategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Sub sub level category with this id not found.")

    shop_sub_category_item_data = []
    for item in subCategoryInDb.sub_sub_category_level:
        subCategoryItem_data = jsonable_encoder(item)
        category_translation = config_crud.get_localization(item.translation_key, db)
        subCategoryItem_data['translations'] = category_translation
        shop_sub_category_item_data.append(subCategoryItem_data)

    return templates.TemplateResponse("/pages/shop/sub-subcategory-items-level-page.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "flash_message": flash_message,
                                       "sub_category": subCategoryInDb,
                                       "sub_categories_items": shop_sub_category_item_data,
                                       "active_page": "subcategory-page"})


def edit_sub_category(request: Request, data: dict, subcategory_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    categoryInDb = db.query(shop_models.SubCategory).filter_by(id=subcategory_id).first()

    if not categoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found.")

    if data.get('name'):
        title = data['name']

        localization_data = {
            categoryInDb.translation_key: {
                "en": title.get('en', ''),
                "fr": title.get('fr', ''),
                "he": title.get('he', '')
            },
        }

        config_crud.add_translation(localization_data, db)

        categoryInDb.name = emoji.replace_emoji(data['name'].get('en', ''), replace='').lstrip()

        data.pop('name')

    for key, value in data.items():
        setattr(categoryInDb, key, value)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop category updated successfully."}

    return True


def add_sub_category(request: Request, sub_category_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    title = sub_category_data['title']

    en_title = title.get('en', '').strip()
    if not en_title:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Sub Category name is required."
        }
        return True

    sub_category_trans_key =en_title.lower()

    localization_data = {
        sub_category_trans_key: {
            "en": title.get('en', ''),
            "fr": title.get('fr', ''),
            "he": title.get('he', '')
        },
    }

    config_crud.add_translation(localization_data, db)
    unique_id = str(uuid4())

    sub_category_count = db.query(shop_models.SubCategory).filter(
        shop_models.SubCategory.category_id == sub_category_data.get('parent_category_id')).count()
    if sub_category_count >= 5:
        request.session["flash_message"] = {"type": "error",
                                            "message": "Maximum of 5 subcategories already added."}

        return True

    subCategoryModel = shop_models.SubCategory(
        id=unique_id,
        name=en_title.capitalize(),
        category_id=sub_category_data.get('parent_category_id'),
        translation_key=sub_category_trans_key,
    )

    db.add(subCategoryModel)
    db.commit()
    db.refresh(subCategoryModel)

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop category added successfully."}

    return True


def add_sub_category_item(request: Request, sub_category_id: str, item_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    title = item_data['title']

    sub_category_trans_key = title.get('en').lower()

    localization_data = {
        sub_category_trans_key: {
            "en": title.get('en', ''),
            "fr": title.get('fr', ''),
            "he": title.get('he', '')
        },
    }

    config_crud.add_translation(localization_data, db)
    unique_id = str(uuid4())

    subCategoryItemModel = shop_models.SubCategoryItems(
        id=unique_id,
        name=title.get('en'),
        sub_category_id=sub_category_id,
        translation_key=sub_category_trans_key,
    )

    db.add(subCategoryItemModel)
    db.commit()
    db.refresh(subCategoryItemModel)

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop category item added successfully."}

    return True

def add_sub_sub_category_item(request: Request, sub_category_id: str, item_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    title = item_data['title']

    sub_category_trans_key = title.get('en').lower()

    localization_data = {
        sub_category_trans_key: {
            "en": title.get('en', ''),
            "fr": title.get('fr', ''),
            "he": title.get('he', '')
        },
    }

    config_crud.add_translation(localization_data, db)

    subCategoryItemModel = shop_models.SubSubCategoryItems(
        name=title.get('en'),
        sub_category_id=sub_category_id,
        translation_key=sub_category_trans_key,
    )

    db.add(subCategoryItemModel)
    db.commit()
    db.refresh(subCategoryItemModel)

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop category item added successfully."}



def add_sub_sub_category_level_item(request: Request, sub_category_id: str, item_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    title = item_data['title']

    sub_category_trans_key = title.get('en').lower()

    localization_data = {
        sub_category_trans_key: {
            "en": title.get('en', ''),
            "fr": title.get('fr', ''),
            "he": title.get('he', '')
        },
    }

    config_crud.add_translation(localization_data, db)

    subCategoryItemModel = shop_models.SubSubCategoryItemsLevel(
        name=title.get('en'),
        sub_category_id=sub_category_id,
        translation_key=sub_category_trans_key,
    )

    db.add(subCategoryItemModel)
    db.commit()
    db.refresh(subCategoryItemModel)

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop sub-category level item added successfully."}



def delete_sub_category(request: Request, subcategory_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    subCategoryInDb = db.query(shop_models.SubCategory).filter_by(id=subcategory_id).first()

    if not subCategoryInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found.")

    db.delete(subCategoryInDb)
    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Sub Category deleted successfully."}

    return True


def delete_sub_category_item(request: Request, item_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    subCategoryItemInDb = db.query(shop_models.SubCategoryItems).filter_by(id=item_id).first()

    if not subCategoryItemInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Category with this id not found.")

    db.delete(subCategoryItemInDb)
    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Sub category item deleted successfully."}

    return True


# =======> App Colors section start <=======
def get_colors(request: Request, db: Session, page: int, limit: int):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    offset = (page - 1) * limit
    search_q = request.query_params.get("q")
    color_query = db.query(shop_models.Colors)
    if search_q:
        color_query = color_query.filter(
            shop_models.Colors.color_name.ilike(f"%{search_q}%")
        )

    total_colors = color_query.count()

    colorsInDb = (
        color_query
        .order_by(shop_models.Colors.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    shop_color_data = []
    for color in colorsInDb:
        color_data = jsonable_encoder(color)
        color_translation = config_crud.get_localization(color.translation_key, db)
        color_data['translations'] = color_translation
        shop_color_data.append(color_data)

    return templates.TemplateResponse("/pages/shop/colors-page.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "colors": shop_color_data,
                                       "flash_message": flash_message,
                                       "active_page": "colors-page",
                                       "total": total_colors,
                                       "page": page,
                                       "limit": limit,
                                       })


def edit_color(request: Request, color_id: str, color_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    color_title = color_data['color_name']

    color_trans_key = color_title.get('en').lower()

    localization_data = {
        color_trans_key: {
            "en": color_title.get('en', ''),
            "fr": color_title.get('fr', ''),
            "he": color_title.get('he', '')
        },
    }

    config_crud.add_translation(localization_data, db)

    colorInDb = db.query(shop_models.Colors).filter_by(id=color_id).first()

    colorInDb.color_name = color_title.get('en')
    colorInDb.translation_key = color_trans_key
    colorInDb.color_code = color_data['color_code']

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop color edited successfully."}

    return True


def delete_color(request: Request, color_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    colorInDb = db.query(shop_models.Colors).filter_by(id=color_id).first()

    if not colorInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Color with this id not found.")

    db.delete(colorInDb)
    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Color deleted successfully."}

    return True

def add_new_color(request: Request, color_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    color_title = (color_data.get('color_title', {}).get('en') or "").strip()
    color_code = (color_data.get('color_code') or "").strip()

    if not color_title:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Color name is required."
        }
        return True

    if not color_code:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Color code is required."
        }
        return True

    color_code = color_code.upper()
    color_pattern = r"^#[A-F0-9]{6}$"

    if not re.match(color_pattern, color_code):
        request.session["flash_message"] = {
            "type": "error",
            "message": "Please enter valid color code.."
        }
        return True

    category_trans_key = color_title.lower()

    localization_data = {
        category_trans_key: {
            "en": color_title,
            "fr": (color_data.get('color_title', {}).get('fr') or "").strip(),
            "he": (color_data.get('color_title', {}).get('he') or "").strip()
        },
    }

    config_crud.add_translation(localization_data, db)
    unique_id = str(uuid4())

    colorModel = shop_models.Colors(
        id=unique_id,
        color_name=color_title,
        color_code=color_code,
        translation_key=category_trans_key,
    )

    try:
        db.add(colorModel)
        db.commit()
        db.refresh(colorModel)

        request.session["flash_message"] = {"type": "success",
                                            "message": "Shop color added successfully."}
        return True

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="Color with this name already exists.")

# =======> App Colors section end <=======

# =======> App Brands section start <=======
def get_brands(request: Request, db: Session, page: int, limit: int):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    offset = (page - 1) * limit
    search_q = request.query_params.get("q")

    query = db.query(shop_models.Brands)

    if search_q:
        query = query.filter(
            shop_models.Brands.name.ilike(f"%{search_q}%")
        )
    total_brands = query.count()

    brandsInDb = query.offset(offset).limit(limit).all()

    shop_brand_data = []
    for brand in brandsInDb:
        color_data = jsonable_encoder(brand)
        shop_brand_data.append(color_data)

    return templates.TemplateResponse(
        "/pages/shop/brands-page.html",
        {
            "request": request,
            "current_user": current_user,
            "brands": shop_brand_data,
            "total": total_brands,
            "page": page,
            "limit": limit,
            "flash_message": flash_message,
            "active_page": "brands-page",
        }
    )

def edit_brand(request: Request, brand_id: str, brand_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    brandInDb = db.query(shop_models.Brands).filter_by(id=brand_id).first()

    for key, value in brand_data.items():
        setattr(brandInDb, key, value)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop brand edited successfully."}

    return True


def add_brand(request: Request, brand_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    unique_id = str(uuid4())

    # brandModel = shop_models.Brands(
    #     id=unique_id,
    #     name=brand_data.get('brand_name').capitalize()
    # )
    brand_name = (brand_data.get('brand_name') or "").strip()

    if not brand_name:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Brand name is required."
        }
        return True

    brandModel = shop_models.Brands(
        id=unique_id,
        name=brand_name.capitalize()
    )

    try:
        db.add(brandModel)
        db.commit()
        db.refresh(brandModel)

        request.session["flash_message"] = {"type": "success",
                                            "message": "Brand added successfully."}

        return True

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="Brand with this name already exists.")

    # for key, value in brand_data.items():
    #     setattr(brandInDb, key, value)
    #
    # db.commit()
    #
    #
    # request.session["flash_message"] = {"type": "success",
    #                                     "message": "Shop brand edited successfully."}
    #
    # return True


def delete_brand(request: Request, brand_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    brandInDb = db.query(shop_models.Brands).filter_by(id=brand_id).first()

    db.delete(brandInDb)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop brand deleted successfully."}

    return True


# =======> App Brands section end <=======


# =======> App Sizes section start <=======
def get_sizes(request: Request, db: Session, page: int = 1, limit: int = 10):
    flash_message = request.session.pop("flash_message", None)
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    offset = (page - 1) * limit
    search_q = request.query_params.get("q")

    size_query = db.query(shop_models.Sizes)

    if search_q:
        size_query = size_query.filter(
            shop_models.Sizes.size.ilike(f"%{search_q}%")
        )

    total_sizes = size_query.count()

    sizesInDb = (
        size_query
        .order_by(shop_models.Sizes.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    shop_size_data = []
    for size in sizesInDb:
        size_data = jsonable_encoder(size)
        shop_size_data.append(size_data)

    return templates.TemplateResponse("/pages/shop/sizes-page.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "sizes": shop_size_data,
                                       "flash_message": flash_message,
                                       "active_page": "sizes-page",  "total": total_sizes,"page": page,"limit": limit})

def get_shoes_sizes(request: Request, db: Session, current_user, page: int, limit: int):
    flash_message = request.session.pop("flash_message", None)
    size_type = shop_schemas.ShoesSizeType

    offset = (page - 1) * limit
    search_q = request.query_params.get("q")

    size_query = db.query(shop_models.ShoeSizes)

    if search_q:
        size_query = size_query.filter(
            or_(
                shop_models.ShoeSizes.size.ilike(f"%{search_q}%")
            )
        )

    total_sizes = size_query.count()

    shoes_size_data = (
        size_query
        .order_by(
            case(
                (shop_models.ShoeSizes.size.op("~")('^[0-9]+(\\.[0-9]+)?$'),
                 cast(shop_models.ShoeSizes.size, Float)),
                else_=None
            ).asc(),
            shop_models.ShoeSizes.size.asc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return templates.TemplateResponse(
        "/pages/shop/shoes-sizes-page.html",
        {
            "request": request,
            "current_user": current_user,
            "sizes": shoes_size_data,
            "flash_message": flash_message,
            "active_page": "shoes-sizes-page",
            "size_type": size_type,
            "total": total_sizes,
            "page": page,
            "limit": limit,
        }
    )


def create_shoes_sizes(formData: schemas.CreateShoesSize, db):
    size = shop_models.ShoeSizes(
        size=formData.size,
        type=formData.type
    )
    db.add(size)
    db.commit()
    return HTTPException(status_code=201, detail="Size added successfully.")


def update_shoes_sizes(formData: schemas.CreateShoesSize, db, obj_id):
    size = db.query(shop_models.ShoeSizes).filter(shop_models.ShoeSizes.id == obj_id).first()
    if not size:
        return HTTPException(status_code=404, detail="Invalid object id not found.")

    size.size = formData.size
    size.type = formData.type
    db.commit()
    return HTTPException(status_code=200, detail="Size update successfully.")


def delete_shoes_size(obj_id, db: Session):
    try:
        size = db.query(shop_models.ShoeSizes).filter(shop_models.ShoeSizes.id == obj_id).first()
        db.delete(size)
        db.commit()
        return HTTPException(status_code=200, detail="Size deleted successfully.")
    except Exception as e:
        return HTTPException(status_code=400, detail=f"Size deleted failed due to {str(e)}.")


def add_size(request: Request, size_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    unique_id = str(uuid4())

    sizeModel = shop_models.Sizes(
        id=unique_id,
        size=size_data.get('size')
    )

    try:
        db.add(sizeModel)
        db.commit()
        db.refresh(sizeModel)

        request.session["flash_message"] = {"type": "success",
                                            "message": "Sizes added successfully."}

        return True

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="Sizes with this name already exists.")


def edit_size(request: Request, size_id: str, size_data: dict, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    sizeInDb = db.query(shop_models.Sizes).filter_by(id=size_id).first()

    for key, value in size_data.items():
        setattr(sizeInDb, key, value)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Shop size edited successfully."}

    return True


def delete_size(request: Request, size_id: str, db: Session):
    current_user = get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    sizeInDb = db.query(shop_models.Sizes).filter_by(id=size_id).first()

    if not sizeInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Size with this id not found.")

    db.delete(sizeInDb)
    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Color deleted successfully."}

    return True


def get_current_admin(request: Request, db: Session):
    try:
        token = request.cookies.get('access_token')
        if token is None:
            return None
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        email_address: str = payload.get("sub")
        current_admin = get_admin(email_address, db)
        if not current_admin:
            return None
        return get_admin_profile(current_admin)

    except Exception as e:
        print(e)
        return None


def get_admin(email_address: str, db: Session):
    return db.query(models.Administrator).filter(models.Administrator.email_address == email_address).first()


def get_admin_profile(user: models.Administrator):
    adminInDbSchema = schemas.AdminInDb.model_validate(user)
    adminInDbSchema.profile_pic = adminInDbSchema.profile_picture
    return adminInDbSchema


def update_admin_password(db: Session, new_password: str, email_address: str):
    try:
        user = db.query(Administrator).filter(Administrator.email_address == email_address).first()
        password_hash = get_password_hash(new_password)
        user.password = password_hash
        db.commit()
        db.refresh(user)
        return True
    except:
        return None


def get_user_statistic(db: Session):
    seven_day_ago = (datetime.utcnow() - timedelta(days=6)).replace(hour=0, minute=0, second=0,
                                                                    microsecond=0)
    result = (
        db.query(
            func.date(auth_models.User.date_created).label("day"),
            func.count(auth_models.User.id).label("user_count")
        )
        .filter(auth_models.User.date_created >= seven_day_ago)
        .group_by(func.date(auth_models.User.date_created))
        .order_by(func.date(auth_models.User.date_created))
        .all()
    )

    dates, labels = [], []
    for i in range(7):
        day = (datetime.utcnow() - timedelta(days=6) + timedelta(days=i)).date()
        day_count = next((row.user_count for row in result if row.day == day), 0)
        dates.append(str(day.strftime("%d %b")))
        labels.append(day_count)

    # growth
    now = datetime.utcnow()
    start_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_last_month = (start_of_this_month - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0,
                                                                            microsecond=0)
    end_of_last_month = start_of_this_month - timedelta(microseconds=1)

    # Count users
    current_users = db.query(auth_models.User).filter(auth_models.User.date_created >= start_of_this_month).count()
    previous_users = db.query(auth_models.User).filter(
        auth_models.User.date_created >= start_of_last_month,
        auth_models.User.date_created <= end_of_last_month
    ).count()

    # Calculate growth percentage
    if previous_users == 0:
        growth_percent = 100.0 if current_users > 0 else 0.0
    else:
        growth_percent = round((current_users - previous_users) / previous_users * 100, 1)

    if growth_percent < 0:
        growth_percent = 0

    return dates, labels, growth_percent


def get_items_statistic(db: Session):
    seven_day_ago = (datetime.utcnow() - timedelta(days=6)).replace(
        day=1, hour=0, minute=0, second=0,
        microsecond=0
    )

    top_categories = (
        db.query(
            shop_models.ShopItem.category,
            func.count(shop_models.ShopItem.id).label("item_count")
        )
        .filter(shop_models.ShopItem.date_created >= seven_day_ago)
        .group_by(shop_models.ShopItem.category)
        .order_by(func.count(shop_models.ShopItem.id).desc())
        .limit(10)
        .all()
    )

    # growth
    start_of_this_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_last_month = (start_of_this_month - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0,
                                                                            microsecond=0)
    end_of_last_month = start_of_this_month - timedelta(microseconds=1)

    current_items = db.query(auth_models.User).filter(shop_models.ShopItem.date_created >= start_of_this_month).count()

    # previous_items = db.query(auth_models.User).filter(
    #     shop_models.ShopItem.date_created >= start_of_last_month,
    #     shop_models.ShopItem.date_created <= end_of_last_month
    # ).count()

    previous_items = db.query(auth_models.User).join(auth_models.User.shop_items).filter(
        shop_models.ShopItem.date_created >= start_of_last_month,
        shop_models.ShopItem.date_created <= end_of_last_month
    ).distinct().count()

    if previous_items == 0:
        growth_percent = 100.0 if current_items > 0 else 0.0
    else:
        growth_percent = round((current_items - previous_items) / previous_items * 100, 1)
    if growth_percent < 0:
        growth_percent = 0
    return growth_percent, [{"x": i[0], "y": i[1]} for i in top_categories]


def get_top_brands_stats(db: Session, limit: int = 7):
    top_brands = (
        db.query(shop_models.ShopItem.brand, func.count(shop_models.ShopItem.id).label("count"))
        .group_by(shop_models.ShopItem.brand)
        .order_by(func.count(shop_models.ShopItem.id).desc())
        .limit(limit)
        .all()
    )
    return [{"x": i[0], "y": i[1]} for i in top_brands]


def disabled_user(db: Session, user_id, request: Request):
    try:
        reported_user = db.query(auth_models.User).filter(auth_models.User.id == user_id).first()
        reported_user.account_status = auth_models.AccountStatus.Disabled
        db.commit()

        request.session["flash_message"] = {"type": "success",
                                            "message": f"user {reported_user.profile.username} is deactivate successfully."}
    except Exception as e:
        print(e)
        request.session["flash_message"] = {"type": "error",
                                            "message": f"user deactivation failed."}
    return True


def add_forum_topic(db: Session, request: Request, formData, current_user):
    uploaded_image_urls = []
    title = (formData.get("title") or "").strip()
    description = (formData.get("description") or "").strip()

    if not title:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Title is required."
        }
        return RedirectResponse("/admin/forum/topics", status_code=303)

    if not description:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Description is required."
        }
        return RedirectResponse("/admin/forum/topics", status_code=303)

    for image in formData.getlist('images'):
        if image.size > 0:
            result = upload(
                image.file,
                folder=f"Sold/Topics/{current_user.id}",
                public_id=image.filename.split('.')[0],
                overwrite=True
            )
            uploaded_image_urls.append(result['secure_url'])

    ForumTopic = forum_model.ForumTopic(
        category=formData.get("category"),
        title=title,
        description=description,
        images=json.dumps(uploaded_image_urls),
        admin_id=current_user.id
    )
    db.add(ForumTopic)
    db.commit()
    db.refresh(ForumTopic)
    request.session["flash_message"] = {"type": "success",
                                        "message": f"Forum topic add successfully."}

    return True


def add_material(request: Request, db, formData):
    title = formData.get("name")
    material_trans_key = title.lower()

    localization_data = {
        material_trans_key: {
            "en": formData.get("name"),
            "fr": formData.get("name_fr"),
            "he": formData.get("name_he")
        },
    }

    config_crud.add_translation(localization_data, db)

    material = shop_models.ItemMaterial(
        name=formData.get("name"),
        translation_key=material_trans_key
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    request.session["flash_message"] = {
        "type": "success",
        "message": f"Item material add successfully."
    }
    return True


def update_material(request, db, formData):
    MaterialInDb = db.query(shop_models.ItemMaterial).filter(shop_models.ItemMaterial.id == formData.get("id")).first()

    if not MaterialInDb:
        request.session["flash_message"] = {
        "type": "error",
        "message": f"Item material not found."
    }

    if MaterialInDb.translation_key:
        translation_key = MaterialInDb.translation_key
    else:
        title = formData.get("name")
        translation_key = title.lower()
        MaterialInDb.translation_key = translation_key

    localization_data = {
            translation_key: {
            "en": formData.get("name"),
            "fr": formData.get("name_fr"),
            "he": formData.get("name_he")
            },
        }

    config_crud.add_translation(localization_data, db)
    MaterialInDb.name = formData.get("name")
    db.commit()
    request.session["flash_message"] = {
        "type": "success",
        "message": f"Item material update successfully."
    }
    return True


def delete_material(request, db, material_id):
    MaterialInDb = db.query(shop_models.ItemMaterial).filter(
        shop_models.ItemMaterial.id == material_id).first()
    db.delete(MaterialInDb)
    db.commit()
    request.session["flash_message"] = {
        "type": "success",
        "message": f"Item material delete successfully."
    }
    return True

def add_search_suggestion_term(item_id, request, db, formData):
    term = (formData.get("term") or "").strip()
    if not term:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Search suggestion is required."
        }
        return RedirectResponse(
            url=f"/admin/shop/item/{item_id}/search-suggestion",
            status_code=303
        )
    SearchSuggestion = shop_models.SearchSuggestion(
        item_id=item_id,
        term=term
    )
    db.add(SearchSuggestion)
    db.commit()
    db.refresh(SearchSuggestion)
    request.session["flash_message"] = {
        "type": "success",
        "message": f"Search suggestion added successfully."
    }
    return RedirectResponse(url=f"/admin/shop/item/{item_id}/search-suggestion", status_code=303)

def delete_search_suggestion_term(term_id, db, request):
    try:
        SearchSuggestion = db.query(shop_models.SearchSuggestion).filter(
            shop_models.SearchSuggestion.id == term_id).first()
        db.delete(SearchSuggestion)
        db.commit()
        request.session["flash_message"] = {
            "type": "success",
            "message": f"Search suggestion deleted successfully."
        }
    except Exception as e:
        request.session["flash_message"] = {
            "type": "success",
            "message": f"Search suggestion deletion failed due to {str(e)}."
        }
    return True


def add_pickup_point(formData, db: Session, request: Request):
    PickPoint = shop_models.DeliveryPickUpPoint(
        city=formData.get('city'),
        zipcode=formData.get("zipcode"),
        address=formData.get("address")
    )
    db.add(PickPoint)
    db.commit()
    request.session["flash_message"] = {
        "type": "success",
        "message": f"Pickup address added successfully."
    }
    return RedirectResponse(url=f"/admin/item/pickup-points", status_code=303)


def update_pickup_point(formData, db: Session, request: Request, point_id):
    try:
        PickPoint = db.query(shop_models.DeliveryPickUpPoint).filter(
            shop_models.DeliveryPickUpPoint.id == point_id
        ).first()
        PickPoint.city = formData.get("city", PickPoint.city)
        PickPoint.zipcode = formData.get("zipcode", PickPoint.zipcode)
        PickPoint.address = formData.get("address", PickPoint.address)
        db.commit()
        request.session["flash_message"] = {
            "type": "success",
            "message": f"Pickup point update successfully."
        }
    except Exception as e:
        request.session["flash_message"] = {
            "type": "error",
            "message": f"Pickup point update failed due to {str(e)}"
        }
    return RedirectResponse(url=f"/admin/item/pickup-points", status_code=303)


def delete_pickup_point(db, request, point_id):
    try:
        PickPoint = db.query(shop_models.DeliveryPickUpPoint).filter(
            shop_models.DeliveryPickUpPoint.id == point_id
        ).first()

        db.delete(PickPoint)
        db.commit()
        request.session["flash_message"] = {
            "type": "success",
            "message": f"pickup point deleted successfully."
        }

    except Exception as e:
        request.session["flash_message"] = {
            "type": "error",
            "message": f"Pickup point delete failed due to {str(e)}"
        }
    return RedirectResponse(url=f"/admin/item/pickup-points", status_code=303)
