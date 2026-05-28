import json
import os
from typing import Optional
from uuid import uuid4

import cloudinary
import requests
from cloudinary.uploader import upload
from fastapi import APIRouter, Depends, Query, Body
from fastapi.encoders import jsonable_encoder

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from starlette import status as starlette_status
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates

import forum.models
import main
import payment.models
from appconfig import models as config_models, schemas as config_schemas, crud as config_crud
from appconfig.crud import update_env
from appconfig.schemas import AppEnv
from auth import crud as auth_crud, models as auth_models, schemas as auth_schemas
from cms import crud as cms_crud, models as cms_models, schemas as cms_schemas
from dependency import get_db, get_env
from exception import UnicornException
from forum import crud as forum_crud
from forum import models as forum_models
from forum import schemas as forum_schema
from helper import create_access_token
from shop import schemas as shop_schemas
from admin.services import *
from admin.crud import update_admin_password
from admin.template_tags import item_image_format, list_to_str, subscription_status, str_list_to_list
from subscription import models as subscription_model
from datetime import datetime, timedelta
from shop import models as shop_model
from others import models as other_models
from fastapi.responses import RedirectResponse
from sqlalchemy import or_

from affiliated import crud as affiliated_crud, schemas as affiliated_schemas, models as affiliate_models

templates = Jinja2Templates(directory="templates")
TRANSLATIONS_DIR = "I18n"
router = APIRouter(
    prefix="/admin", tags=['Admin']
)

templates.env.filters["item_image_format"] = item_image_format
templates.env.filters["list_to_str"] = list_to_str
templates.env.filters["subscription_status"] = subscription_status
templates.env.filters["str_list_to_list"] = str_list_to_list


@router.get("", tags=["Admin"])
async def home(request: Request, db: Session = Depends(get_db)):
    current_admin = await get_current_admin(request, db)
    if not current_admin:
        return RedirectResponse("/admin/login")
    else:
        return RedirectResponse("/admin/dashboard")


@router.post("/create-super-user", tags=["Admin"])
async def create_super_user(user_data: schemas.AdminCreate, db: Session = Depends(get_db)):
    unique_id = str(uuid4())
    userDataDict = user_data.model_dump()

    userDataDict['id'] = unique_id
    userDataDict['password'] = auth_crud.get_password_hash(user_data.password)

    adminModel = models.Administrator(**userDataDict)
    try:
        db.add(adminModel)
        db.commit()
        db.refresh(adminModel)
        user_details = schemas.AdminInDb.model_validate(adminModel)

        return {"message": "Super user created successfully",
                "data": user_details, "status": True}

    except IntegrityError:
        raise UnicornException(status_code=status.HTTP_409_CONFLICT,
                               message="User with this email address already exists.")


# authentication

@router.get("/login", tags=["Admin"])
async def login(request: Request, db: Session = Depends(get_db)):
    flash_message = request.session.pop("flash_message", None)
    current_user = await get_current_admin(request, db)
    if current_user:
        return RedirectResponse("/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("/pages/login.html",
                                      {"request": request, "flash_message": flash_message})


@router.post("/login", tags=["Admin"])
async def login(response: Response, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    email_address = form.get('email_address')
    password = form.get('password')

    admin_user = authenticate_admin_user(email_address, password, db)

    if not admin_user:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message='Email or password is incorrect')

    access_token = create_access_token(admin_user.email_address)
    cookie_value = f"Bearer {access_token}"

    response.set_cookie(key="access_token", value=cookie_value, httponly=True, secure=False)

    return True


@router.get('/sign-out', tags=['Admin'])
async def sign_out(response: Response):
    response.delete_cookie("access_token", path="/")
    return RedirectResponse("/admin/login", status_code=302, headers=response.headers)


@router.get("/change-password", tags=["Admin"])
async def change_password_get(request: Request, current_user=Depends(require_login)):
    flash_message = request.session.pop("flash_message", None)
    form = {}
    return templates.TemplateResponse("/pages/settings.html", {"request": request,
                                                               "current_user": current_user,
                                                               "flash_message": flash_message,
                                                               "active_page": "settings",
                                                               "form": form})


@router.post(path="/change-password", tags=['Admin'])
async def change_password(request: Request, db: Session = Depends(get_db), current_user=Depends(require_login)):
    form = await request.form()
    is_verify = authenticate_admin_user(
        email_address=current_user.email_address,
        password=form.get('old-password'),
        db=db
    )
    if is_verify is not None:
        if str(form.get("new-password")) != str(form.get("retype-password")):
            flash_message = {"type": "error", "message": "New password and retype new password does n't match!"}
        else:
            new_password = form.get("new-password")
            if update_admin_password(db=db, new_password=new_password, email_address=current_user.email_address):
                flash_message = {"type": "success", "message": "Password changed successfully!"}
            else:
                flash_message = {"type": "error", "message": "Password change failed!"}
    else:
        flash_message = {"type": "error", "message": "Incorrect old password!"}

    return templates.TemplateResponse("/pages/settings.html", {"request": request,
                                                               "current_user": current_user,
                                                               "flash_message": flash_message,
                                                               "active_page": "settings",
                                                               "form": form})


# end authentication

@router.get("/dashboard", tags=["Admin"])
async def dashboard(request: Request, db: Session = Depends(get_db), current_user=Depends(require_login)):
    # users
    total_users = db.query(auth_models.User).count()
    dates, data, growth_percent = crud.get_user_statistic(db=db)

    # category
    total_category = db.query(shop_model.Category).count()
    category_growth_percent, category_statics = crud.get_items_statistic(db)

    # top brand
    total_brands = db.query(shop_model.Brands).count()
    top_brand_stats = crud.get_top_brands_stats(db=db)
    return templates.TemplateResponse("/pages/dashboard.html", locals())


# =======> App cms section <=======
@router.get("/api/cms", tags=["Admin"])
async def get_all_cms(request: Request, db: Session = Depends(get_db)):
    cmsInDb = db.query(cms_models.Cms).all()
    return [cms_schemas.CmsInDb.model_validate(cms) for cms in cmsInDb]


@router.get("/cms/new", tags=["Admin"])
async def add_cms(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    flash_message = request.session.pop("flash_message", None)
    return templates.TemplateResponse("/pages/cms/add-new.html",
                                      {"request": request, "current_user": current_user,
                                       "active_page": 'addCms', "flash_message": flash_message})

from fastapi.responses import JSONResponse
@router.post("/api/cms", tags=["Admin"])
async def add_cms(request: Request, data: dict, db: Session = Depends(get_db)):
    print("DATA RECEIVED:", data)
    current_user = await get_current_admin(request, db)
    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    has_valid_title = bool(data.get("title", {}).get("en", "").strip())
    print("has_valid_title", has_valid_title)
    if not has_valid_title:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Title is required"
        }
        return RedirectResponse("/admin/cms/new", status_code=status.HTTP_303_SEE_OTHER)

    else:
        unique_id = str(uuid4())

        cmsModel = cms_models.Cms(
            id=unique_id,
            slug=data['slug'],
        )
        data.pop('slug', None)

        cmsContent = {
            'en': {},
            'fr': {},
            'he': {}
        }

        for key in data.keys():
            for lang in data[key]:
                cmsContent[lang][key] = data[key][lang]

        cmsModel.content = json.dumps(cmsContent)

        db.add(cmsModel)
        db.commit()
    return False

@router.delete("/api/cms/{slug}", tags=["Admin"])
async def delete_cms(request: Request, slug: str, db: Session = Depends(get_db)):
    cmsInDb = db.query(cms_models.Cms).filter_by(slug=slug).first()

    if not cmsInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="cms with this slug does not exist")

    db.delete(cmsInDb)
    db.commit()

    return True


@router.get("/cms/{slug}", tags=["Admin"])
async def get_cms(request: Request, slug: str, lang: Optional[str] = "en", db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    cmsInDb = cms_crud.get_cms(slug, db)
    cms_content = cmsInDb.content

    if current_user:
        return templates.TemplateResponse("/pages/cms/cms.html",
                                          {"request": request, "current_user":
                                              current_user,
                                           "cms_title": cms_content[lang].get(
                                               'title') if lang in cms_content else "",
                                           "cms_content": cms_content[lang].get(
                                               'content') if lang in cms_content else "",
                                           "lang": lang,
                                           "page": "cms",
                                           "active_page": slug, "cms": cmsInDb})


@router.get("/cms/edit/{slug}", tags=["Admin"])
async def edit_cms(request: Request, slug: str, lang: Optional[str] = "en", db: Session = Depends(get_db)):
    flash_message = request.session.pop("flash_message", None)
    current_user = await get_current_admin(request, db)
    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    cmsInDb = db.query(cms_models.Cms).filter(cms_models.Cms.slug == slug).first()
    cmsSchema = cms_schemas.CmsInDb.model_validate(cmsInDb)

    cms_title = {}
    cms_content = {}

    for key in cmsSchema.content.keys():
        if cmsSchema.content[key]:
            cms_title[key] = cmsSchema.content[key].get('title', '')
            cms_content[key] = cmsSchema.content[key].get('content', '')

    return templates.TemplateResponse("/pages/cms/edit.html",
                                      {"request": request, "current_user": current_user,
                                       "cms_title": cms_title,
                                       "cms_content": cms_content,
                                       "flash_message": flash_message,
                                       "cms_slug": cmsInDb.slug,
                                       "lang": lang, "page": "cms",
                                       "active_page": slug, "cms": cmsSchema})


@router.patch("/api/cms/edit/{slug}", tags=["Admin"])
async def edit_cms(request: Request, slug: str, data: dict, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    cmsInDb = db.query(cms_models.Cms).filter(cms_models.Cms.slug == slug).first()

    cmsContent = {
        'en': {},
        'fr': {},
        'he': {}
    }
    for key in data.keys():
        for lang in data[key]:
            cmsContent[lang][key] = data[key][lang]

    cmsInDb.content = json.dumps(cmsContent)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Cms content updated successfully"}

    return True


@router.patch("/cms/{slug}", tags=["Admin"])
async def update_cms(cms_data: cms_schemas.Cms, lang: str, slug: str, db: Session = Depends(get_db)):
    return cms_crud.update_cms(cms_data, lang, slug, db)


# =======> App cms section end <=======


# =======> App banners section <=======

@router.get("/banners", tags=["Admin"])
async def get_sliders(request: Request, db: Session = Depends(get_db), q: str = Query(None), page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    flash_message = request.session.pop("flash_message", None)
    current_user = await get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    query = db.query(config_models.HomeSlider)

    if q:
        query = query.filter(
            config_models.HomeSlider.redirect_path.ilike(f"%{q}%")
        )

    total = query.count()

    offset = (page - 1) * limit

    homeSliderInDb = (
        query
        .order_by(config_models.HomeSlider.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return templates.TemplateResponse("/pages/banners.html",
                                      {"request": request, "flash_message": flash_message,
                                       "current_user": current_user, "banners": [jsonable_encoder(slider) for slider
                                                                                 in homeSliderInDb],
                                       "active_page": "banners", "q": q, "page": page, "limit": limit, "total": total})


@router.post("/api/banner", tags=["Admin"])
async def add_slider(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    form = await request.form()

    unique_id = str(uuid4())

    payload = {
        'id': unique_id,
        'redirect_path': form.get('redirect_path'),
    }

    uploaded_image_url = cloudinary.uploader.upload(form.get('banner_img').file, folder="Sold/Banner")
    payload["slider_image_url"] = uploaded_image_url.get('url')

    sliderModel = config_models.HomeSlider(**payload)

    db.add(sliderModel)
    db.commit()
    db.refresh(sliderModel)

    request.session["flash_message"] = {"type": "success",
                                        "message": "Banner added successfully"}


@router.patch("/api/banner/{banner_id}", tags=["Admin"])
async def update_slider(request: Request, banner_id: str, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if not current_user:
        raise UnicornException(status_code=status.HTTP_401_UNAUTHORIZED,
                               message="Current user is not admin")

    homeSliderInDb = db.query(config_models.HomeSlider).filter_by(id=banner_id).first()

    formData = await request.form()

    if not homeSliderInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Banner with this id not found")

    if formData.get('enabled'):
        if formData.get('enabled') == 'false':
            homeSliderInDb.enabled = False
        elif formData.get('enabled') == 'true':
            homeSliderInDb.enabled = True

    if formData.get('redirect_path'):
        homeSliderInDb.redirect_path = formData.get('redirect_path')

    if formData.get('banner_img'):
        uploaded_image_url = cloudinary.uploader.upload(formData.get('banner_img').file, folder="Sold/Banner")
        homeSliderInDb.slider_image_url = uploaded_image_url.get('url')

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Updated successfully."}

    return True


@router.delete("/api/banner/{banner_id}", tags=["Admin"])
async def delete_slider(request: Request, banner_id: str, db: Session = Depends(get_db)):
    homeSliderInDb = db.query(config_models.HomeSlider).filter_by(id=banner_id).first()

    db.delete(homeSliderInDb)
    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Banner deleted successfully."}

    return True


@router.get('/affiliate-banner', tags=['Admin'])
async def affiliate_banner(request: Request, banner_id: str = Query(None),
                           action: str = Query(None), db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    if action and banner_id:
        try:
            banner = db.query(affiliate_models.AffiliateSlider).filter(
                affiliate_models.AffiliateSlider.id == banner_id
            ).first()

            if action == "delete":
                db.delete(banner)
                db.commit()
                message = "Banner deleted successfully"
            elif action == "status":
                message = "Banner status updated successfully"
                if banner.enabled is True:
                    banner.enabled = False
                else:
                    banner.enabled = True
                db.commit()
                db.refresh(banner)
            else:
                message = "nothing"

            request.session["flash_message"] = {"type": "success",
                                                "message": message}
        except Exception as e:
            print(e)

        finally:
            return RedirectResponse(url="/admin/affiliate-banner", status_code=303)

    banners = db.query(affiliate_models.AffiliateSlider).all()

    flash_message = request.session.pop("flash_message", None)
    return templates.TemplateResponse("/pages/affiliate_banners.html",
                                      {"request": request, "flash_message": flash_message,
                                       "current_user": current_user, "banners": banners,
                                       "active_page": "affiliate_banners"})


@router.post('/affiliate-banner', tags=['Admin'])
async def create_affiliate_banner(request: Request, db: Session = Depends(get_db)):
    try:
        formData = await request.form()
        uploaded_image_url = cloudinary.uploader.upload(formData.get('banner_img').file, folder="Sold/Partner")
        banner = affiliate_models.AffiliateSlider(
            image=uploaded_image_url.get("url"),
            redirect_path=formData.get("redirect_path", "")
        )
        db.add(banner)
        db.commit()
        request.session["flash_message"] = {"type": "success",
                                            "message": "Banner added successfully."}

    except Exception as e:
        request.session["flash_message"] = {"type": "error",
                                            "message": f"{str(e)}"}

    return RedirectResponse(url="/admin/affiliate-banner", status_code=303)

    # =======> App slider section end <=======


# =======> App sizes section <=======
@router.post("/size/new", tags=["Admin"])
async def add_new_size(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    form = await request.form()

    size = form.get('size')
    unique_id = str(uuid4())

    sizeModel = shop_models.Sizes(
        id=unique_id,
        size=size
    )

    db.add(sizeModel)
    db.commit()
    db.refresh(sizeModel)

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message="User account updated successfully.")


@router.get("/sizes", tags=["Admin"])
async def get_sizes(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if current_user:
        all_sizes = []
        sizesInDb = db.query(shop_models.Sizes).all()

        for size in sizesInDb:
            all_sizes.append(shop_schemas.SizeInDb(
                id=size.id,
                size=size.size,
                date_created=size.date_created.strftime("%d-%m-%Y at %-I:%M%p")
            ))

        return templates.TemplateResponse("sizes-page.html",
                                          {"request": request,
                                           "all_sizes": all_sizes,
                                           "current_admin": current_user,
                                           "active_page": "sizes-page"})


@router.delete("/size/{size_id}", tags=["Admin"])
async def delete_size(request: Request, size_id: str, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    sizeInDb = db.query(shop_models.Sizes).filter(shop_models.Sizes.id == size_id).first()

    db.delete(sizeInDb)
    db.commit()

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message="User account updated successfully.")


# =======> App sizes section end <=======


# =======> Account settings section start <=======
@router.get("/settings", tags=["Admin"], include_in_schema=False)
async def settings(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    flash_message = request.session.pop("flash_message", None)
    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("/pages/settings.html", {"request": request,
                                                               "current_user": current_user,
                                                               "flash_message": flash_message,
                                                               "active_page": "settings"})


@router.post("/api/settings/languages/change-status", tags=["Admin"])
async def change_language_status(request: Request, lang_code: str, value: bool, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    if current_user:
        langaugeInDb = db.query(config_models.SupportedLanguage).filter_by(code=lang_code).first()
        langaugeInDb.status = value

        db.commit()

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message="Language status updated successfully.")


@router.patch("/api/settings/profile/update-profile", tags=["Admin"])
async def update_admin_profile(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    if current_user:
        formData = await request.form()
        adminInDb = db.query(models.Administrator).filter_by(id=current_user.id).first()
        adminInDb.fullname = formData.get('admin-name')

        if formData.get('profile_image').size > 0:
            uploaded_image_url = cloudinary.uploader.upload(formData.get('profile_image').file,
                                                            folder=f"Sold/Users/{current_user.id}",
                                                            public_id=current_user.id,
                                                            overwrite=True)
            adminInDb.profile_pic = uploaded_image_url.get('url')

        db.commit()

        request.session["flash_message"] = {"type": "success",
                                            "message": "Profile updated successfully."}
        return True


# =======> Account settings section end <=======


# =======> App Config section <=======
@router.get("/app-config", tags=["Admin"], include_in_schema=False)
async def app_config(request: Request, app_env: AppEnv = Depends(get_env), db: Session = Depends(get_db)):
    print(app_env)
    current_user = await get_current_admin(request, db)
    flash_message = request.session.pop("flash_message", None)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    paymentMethodInDb = db.query(config_models.PaymentMethod).all()

    return templates.TemplateResponse("/pages/app-config.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "app_config": app_env.dict(),
                                       "payment_methods": [config_schemas.PaymentMethodInDb.model_validate(method)
                                                           for method in
                                                           paymentMethodInDb],
                                       "flash_message": flash_message,
                                       "active_page": "app-config"})


@router.post("/api/payment-method", tags=["Admin"])
async def update_pm_status(id: str, status: bool, request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=starlette_status.HTTP_303_SEE_OTHER)
    pmInDb = db.query(config_models.PaymentMethod).filter_by(id=id).first()
    pmInDb.enabled = status

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": f"{pmInDb.name} payment method {'enabled' if status == True else 'disabled'}."}

    return True


@router.patch("/api/payment-method", tags=["Admin"])
async def edit_payment_methods(id: str, request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    formData = await request.form()
    formDataObject = {}

    for key, value in formData.items():
        formDataObject[key] = value

    formDataObject.pop('icon')
    pmInDb = db.query(config_models.PaymentMethod).filter_by(id=id).first()

    if not pmInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Language with this code does not exists")

    if formData.get('icon').size > 0:
        uploaded_image_url = cloudinary.uploader.upload(formData.get('icon').file, folder="Sold/Payment Methods",
                                                        public_id=formData.get('name'),
                                                        overwrite=True)

        formDataObject.update({'icon': uploaded_image_url.get('url')})

    for key, value in formDataObject.items():
        setattr(pmInDb, key, value)

    db.commit()

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message="Payment method updated successfully.")


@router.patch("/api/app-config", tags=["Admin"])
async def update_app_config(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    if current_user:
        formData = await request.form()
        app_icon = formData.get('app_icon')

        if app_icon.size > 0:
            uploaded_image_url = cloudinary.uploader.upload(app_icon.file, folder="Sold/",
                                                            public_id='app-icon',
                                                            overwrite=True)

            update_env('APP_ICON', uploaded_image_url.get('url'))

        update_env('APP_NAME', formData.get('app-name'))
        update_env('CURRENCY_SYMBOL', formData.get('currency-symbol'))
        update_env('SHIPPING_FEE', formData.get('shipping-fee'))
        update_env('FEATURED_DRESSING_PRICE', formData.get('featured-dressing-price'))
        update_env('SUPPORT_EMAIL', formData.get('support-email'))
        update_env('SUPPORT_NUMBER', formData.get('support-phone'))
        update_env('SELLER_MSG', formData.get('seller-msg'))

        # reinitialize the app env
        main.reinitialize_app_env()

        request.session["flash_message"] = {"type": "success",
                                            "message": "Appconfig updated successfully."}

        return True


# =======> App config end <=======


# =======> App language section <=======
@router.get("/languages", tags=["Admin"], include_in_schema=False)
async def app_languages(request: Request, db: Session = Depends(get_db), q: str = Query(None)):
    current_user = await get_current_admin(request, db)
    flash_message = request.session.pop("flash_message", None)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    query = db.query(config_models.SupportedLanguage)

    if q:
        query = query.filter(
            or_(
                config_models.SupportedLanguage.name.ilike(f"%{q}%"),
                config_models.SupportedLanguage.code.ilike(f"%{q}%")
            )
        )

    supportedLanguages = query.order_by(
        desc(config_models.SupportedLanguage.default)
    ).all()

    return templates.TemplateResponse("/pages/languages.html",
                                      {"request": request,
                                       "current_user": current_user,
                                       "languages": [
                                           jsonable_encoder(config_schemas.LanguageInDb.model_validate(language)) for
                                           language in supportedLanguages],
                                       "flash_message": flash_message,
                                       "active_page": "app-languages",
                                       "q": q})


@router.patch("/api/language", tags=["Admin"])
async def update_language(request: Request, code: str, data: dict, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    langaugeInDb = db.query(config_models.SupportedLanguage).filter_by(code=code).first()

    if langaugeInDb:
        for key, value in data.items():
            setattr(langaugeInDb, key, value)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "Language status updated successfully."}

    return True


@router.get("/language/localization", tags=["Admin"], include_in_schema=False)
async def app_localization(request: Request, lang: Optional[str] = "en", search: Optional[str] = "", page: int = Query(1, ge=1),
                           limit: int = Query(20, ge=1), db: Session = Depends(get_db)):

    offset = (page - 1) * limit
    current_user = await get_current_admin(request, db)
    flash_message = request.session.pop("flash_message", None)

    language = db.query(config_models.SupportedLanguage).filter_by(code=lang).first()
    translations = []

    translation_dict = config_crud.get_translation(lang, db)
    for key in translation_dict.keys():
        if search != "":
            search = search.strip()
            if search.lower() not in key.lower() and search.lower() not in str(translation_dict[key]).lower():
                continue

        translations.append({
            'key': key,
            'value': translation_dict[key]
        })

    paginatedData = translations[offset: offset + limit]

    data = {
        "offset": offset,
        "limit": limit,
        "page": page,
        "total": len(translations),
        "data": paginatedData,
    }

    if current_user:
        return templates.TemplateResponse("/pages/localization-page.html",
                                          {"request": request, "current_user":
                                              current_user, "translations": data,
                                           "language_name": language.name,
                                           "flash_message": flash_message,
                                           "lang": lang, "active_page": "app-languages", "search": search}
                                        )


@router.patch("/api/settings/localization", tags=["Admin"])
async def app_localization(lang: str, translation_data: dict = Body(...), db: Session = Depends(get_db)):
    file_path = os.path.join(TRANSLATIONS_DIR, f"{lang}.json")
    if os.path.exists(file_path):
        with open(file_path, "r+", encoding="utf-8") as file:
            existing_translations = json.load(file)
            existing_translations.update({translation_data.get('key'): translation_data.get('value')})
            file.seek(0)
            json.dump(existing_translations, file, ensure_ascii=False, indent=4)
            file.truncate()

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message="Translation edited successfully")


@router.post("/api/localization", tags=["Admin", "Localization"])
async def add_localization(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    formData = await request.form()

    localizationData = {
        formData.get('key'): {
            "en": formData.get('en'),
            "fr": formData.get('fr'),
            "he": formData.get('he')
        }
    }

    result = config_crud.add_translation(localizationData, db)

    request.session["flash_message"] = {"type": "success",
                                        "message": "Translation added successfully."}

    return result


# =======> App language section end <=======


# =======> App notification section <=======
@router.get("/notifications", tags=["Admin"])
async def get_notifications(request: Request, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if current_user:
        return templates.TemplateResponse("/pages/notifications.html",
                                          {"request": request,
                                           "current_user": current_user,
                                           "active_page": "notifications"})


@router.post("/api/notifications", tags=["Admin"])
async def send_notification(request: Request, app_env: AppEnv = Depends(get_env), db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)
    formData = await request.form()

    headers = {
        'Authorization': f'Basic {app_env.onesignal_api_key}',
        'accept': 'application/json',
        'content-type': 'application/json',
    }
    headings = json.loads(formData.get('headings'))
    print("headings", headings)
    has_valid_title = any(
        title and title.strip()
        for title in headings.values()
    )
    print("has_valid_title", has_valid_title)

    if not has_valid_title:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Title is required"
        }
        return RedirectResponse(
            "/admin/notifications",
            status_code=status.HTTP_303_SEE_OTHER
        )

    json_data = {
        "app_id": f"{app_env.onesignal_app_id}",
        "included_segments": [
            "Active Subscriptions"
        ],
        "headings": headings,
        "contents": json.loads(formData.get('contents')),
        "name": "In App Notification"
    }
    result = requests.post('https://onesignal.com/api/v1/notifications', headers=headers, json=json_data)
    request.session["flash_message"] = {
        "type": "success",
        "message": "Notification sent successfully"
    }

    return RedirectResponse(
        "/admin/notifications",
        status_code=status.HTTP_303_SEE_OTHER
    )

# =======> App Notification section end <=======


# =======> App Category and subcategories section end <=======
@router.get("/shop/categories", tags=["Admin"])
async def get_categories(request: Request, page: int = 1, limit: int = 5, db: Session = Depends(get_db)):
    return crud.get_shop_category(request, db, page, limit)


@router.post("/api/shop/category", tags=["Admin"])
async def add_category(request: Request, data: dict, db: Session = Depends(get_db)):
    return crud.add_category(request, data, db)


@router.patch("/api/shop/category/{category_id}", tags=["Admin"])
async def edit_category(request: Request, category_id: str, data: dict, db: Session = Depends(get_db)):
    return crud.edit_category(request, data, category_id, db)


@router.delete("/api/shop/category/{category_id}", tags=["Admin"])
async def delete_category(request: Request, category_id: str, db: Session = Depends(get_db)):
    return crud.delete_category(request, category_id, db)

@router.get("/shop/sub-categories", tags=["Admin"])
async def get_sub_categories(request: Request, page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_shop_sub_category(request, db, page, limit)


@router.get("/shop/sub-categories/{sub_category_id}/items", tags=["Admin"])
async def get_sub_categories_items(request: Request, sub_category_id: str, db: Session = Depends(get_db)):
    return crud.get_shop_sub_category_items(request, sub_category_id, db)


@router.delete("/api/shop/sub-categories/item/{item_id}", tags=["Admin"])
async def delete_sub_category_item(request: Request, item_id: str, db: Session = Depends(get_db)):
    return crud.delete_sub_category_item(request, item_id, db)

@router.get("/shop/sub-sub-categories/level/{item_id}/items", tags=['Admin'])
async def get_sub_sub_categories_level_items(request: Request, item_id: str, db: Session = Depends(get_db)):
    return crud.get_shop_sub_sub_category_level_items(request, item_id, db)


@router.get("/shop/sub-sub-categories/{item_id}/items", tags=['Admin'])
async def get_sub_sub_categories_items(request: Request, item_id: str, db: Session = Depends(get_db)):
    return crud.get_shop_sub_sub_category_items(request, item_id, db)



@router.patch("/api/shop/sub-category/{subcategory_id}", tags=["Admin"])
async def edit_sub_category(request: Request, subcategory_id: str, data: dict, db: Session = Depends(get_db)):
    return crud.edit_sub_category(request, data, subcategory_id, db)


@router.post("/api/shop/sub-category", tags=["Admin"])
async def add_sub_category(request: Request, data: dict, db: Session = Depends(get_db)):
    return crud.add_sub_category(request, data, db)


@router.post("/api/shop/sub-category/{sub_category_id}/item", tags=["Admin"])
async def add_sub_category_item(request: Request, sub_category_id: str, data: dict, db: Session = Depends(get_db)):
    return crud.add_sub_category_item(request, sub_category_id, data, db)

@router.post("/api/shop/sub-sub-category/{sub_category_id}/item", tags=["Admin"])
async def add_sub_sub_category_item(request: Request, sub_category_id: str, data: dict, db: Session = Depends(get_db)):
    return crud.add_sub_sub_category_item(request, sub_category_id, data, db)


@router.post("/api/shop/sub-sub-category/level/{sub_category_id}/item", tags=["Admin"])
async def add_sub_sub_category_level_item(request: Request, sub_category_id: str, data: dict, db: Session = Depends(get_db)):
    return crud.add_sub_sub_category_level_item(request, sub_category_id, data, db)


@router.delete("/api/shop/sub-category/{subcategory_id}", tags=["Admin"])
async def delete_sub_category(request: Request, subcategory_id: str, db: Session = Depends(get_db)):
    return crud.delete_sub_category(request, subcategory_id, db)


# =======> App Category and subcategories section end <=======


# =======> App Colors section start <=======
@router.get("/shop/colors", tags=["Admin"])
async def get_color(request: Request,page: int = 1, limit: int = 10, db: Session = Depends(get_db), ):
    return crud.get_colors(request, db, page, limit)


@router.delete("/api/shop/color/{color_id}", tags=["Admin"])
async def delete_color(request: Request, color_id: str, db: Session = Depends(get_db)):
    return crud.delete_color(request, color_id, db)


@router.post("/api/shop/color", tags=["Admin"])
async def add_new_color(request: Request, color_data: dict, db: Session = Depends(get_db)):
    return crud.add_new_color(request, color_data, db)


@router.patch("/api/shop/color/{color_id}", tags=["Admin"])
async def edit_new_color(request: Request, color_id: str, color_data: dict, db: Session = Depends(get_db)):
    print(color_id)
    return crud.edit_color(request, color_id, color_data, db)


# =======> App Colors section end <=======


# =======> App Size section start <=======
@router.get("/shop/sizes", tags=["Admin"])
async def get_sizes(
        request: Request,
        db: Session = Depends(get_db),
        page: int = 1,
        limit: int = 10
):
    return crud.get_sizes(request, db, page, limit)



@router.delete("/api/shop/size/{size_id}", tags=["Admin"])
async def delete_size(request: Request, size_id: str, db: Session = Depends(get_db)):
    return crud.delete_size(request, size_id, db)


@router.post("/api/shop/size", tags=["Admin"])
async def add_size(request: Request, size_data: dict, db: Session = Depends(get_db)):
    return crud.add_size(request, size_data, db)


@router.patch("/api/shop/size/{size_id}", tags=["Admin"])
async def edit_size(request: Request, size_id: str, size_data: dict, db: Session = Depends(get_db)):
    return crud.edit_size(request, size_id, size_data, db)


@router.get(path="/shop/shoes-size")
async def shoes_size_page(
        request: Request,
        db: Session = Depends(get_db),
        current_user=Depends(require_login),
        page: int = 1,
        limit: int = 10
):
    return crud.get_shoes_sizes(request, db, current_user, page, limit)



@router.post(path="/api/shop/shoes-size")
async def create_shoes_size(data: schemas.CreateShoesSize, db: Session = Depends(get_db),
                            current_user=Depends(get_admin_current_user)):
    return crud.create_shoes_sizes(formData=data, db=db)


@router.delete(path="/api/shop/shoes-size/{obj_id}")
async def delete_shoes_size(
        obj_id,
        db: Session = Depends(get_db),
        current_user=Depends(get_admin_current_user)
):
    return crud.delete_shoes_size(obj_id=obj_id, db=db)


@router.patch(path="/api/shop/shoes-size/{obj_id}")
async def update_shoes_size(obj_id, data: schemas.CreateShoesSize, db: Session = Depends(get_db),
                            current_user=Depends(get_admin_current_user)):
    return crud.update_shoes_sizes(formData=data, db=db, obj_id=obj_id)


# =======> App Size section end <=======

# =======> App Brands section start <=======

@router.get("/shop/brands", tags=["Admin"])
async def get_brands(request: Request, page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_brands(request, db, page, limit)


@router.post("/api/shop/brand", tags=["Admin"])
async def add_brand(request: Request, brand_data: dict, db: Session = Depends(get_db)):
    return crud.add_brand(request, brand_data, db)


@router.patch("/api/shop/brand/{brand_id}", tags=["Admin"])
async def edit_brand(request: Request, brand_id: str, brand_data: dict, db: Session = Depends(get_db)):
    return crud.edit_brand(request, brand_id, brand_data, db)


@router.delete("/api/shop/brand/{brand_id}", tags=["Admin"])
async def delete_brand(request: Request, brand_id: str, db: Session = Depends(get_db)):
    return crud.delete_brand(request, brand_id, db)


# =======> App Brands section end <=======


# =======> App Users section start <=======
@router.get("/users", tags=["Admin"])
async def get_users_list(request: Request, db: Session = Depends(get_db), page: int = 1, limit: int = 10):
    return crud.get_users_list(request, db, page, limit)


@router.patch("/api/user/{user_id}", tags=["Admin"])
async def edit_user(request: Request, user_id: str, db: Session = Depends(get_db)):
    result = await crud.edit_user_account(request, user_id, db)
    return result


@router.delete("/api/user/{user_id}", tags=["Admin"])
async def delete_user(request: Request, user_id: str, db: Session = Depends(get_db)):
    current_user = await get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    userInDb = db.query(auth_models.User).filter_by(id=user_id).first()

    userInDb.account_status = auth_schemas.AccountStatus.Deleted

    allUsers = db.query(auth_models.User).all()

    for user in allUsers:
        user.favourited_items = [item for item in user.favourited_items if item not in userInDb.shop_items]
        user.favorited_topics = [topic for topic in user.favorited_topics if topic not in userInDb.forum_topics]

    db.query(forum.models.ForumTopic).filter_by(user_id=userInDb.id).delete(synchronize_session=False)
    db.query(payment.models.PaymentDetails).filter_by(user_id=userInDb.id).delete(synchronize_session=False)

    db.commit()

    request.session["flash_message"] = {"type": "success",
                                        "message": "User deleted successfully"}

    return True


# @router.get("/shop-products", tags=["Admin"])
# async def get_shop_products(request: Request, db: Session = Depends(get_db)):
#     current_user = await get_current_admin(request, db)
#
#     if current_user:
#         allProductInDb = db.query(shop_models.ShopItem).all()
#
#         allProducts = []
#
#         for product in allProductInDb:
#             allFavouriteItems = db.query(auth_models.favourited_items).filter_by(item_id=product.id).all()
#
#             itemDetailsSchema = shop_schemas.ShopItemDetails.model_validate(product)
#             itemOwnerProfile = profile_crud.get_user_profile_schema(product.owner, db)
#
#             itemOwnerSchema = shop_schemas.ItemOwnerInDb.model_validate(itemOwnerProfile)
#             itemDetailsSchema.owner = itemOwnerSchema
#             itemDetailsSchema.interested_members = len([fav for fav in allFavouriteItems])
#
#             allProducts.append(itemDetailsSchema)
#
#         return admin_templates.TemplateResponse("/pages/shop/all-items.html",
#                                                 {"request": request,
#                                                  "current_admin": current_user,
#                                                  "product_list": allProducts,
#                                                  "active_page": "shop-product-page"})


# @router.get("/shop/items/details/{item_id}", tags=["Admin"])
# async def get_shop_products_details(request: Request, item_id: str, db: Session = Depends(get_db)):
#     current_user = await get_current_admin(request, db)
#
#     if current_user:
#         return admin_templates.TemplateResponse("/pages/shop/item-details.html",
#                                                 {"request": request,
#                                                  "current_admin": current_user,
#                                                  "active_page": "shop-product-page"})


# =======> Forum and community section <=======
from forum.schemas import ForumTopicCategory
from typing import List

from sqlalchemy import cast, String

@router.get("/forum/topics", tags=["Admin"])
async def forum_topics(request: Request, db: Session = Depends(get_db), q: str = Query(None), page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    category_values: List[str] = [category.value for category in ForumTopicCategory]
    flash_message = request.session.pop("flash_message", None)
    current_user = await get_current_admin(request, db)

    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    query = db.query(forum_models.ForumTopic)

    if q:
        query = query.filter(
            or_(
                forum_models.ForumTopic.title.ilike(f"%{q}%"),
                cast(forum_models.ForumTopic.category, String).ilike(f"%{q}%")
            )
        )

    total = query.count()

    offset = (page - 1) * limit

    allForumTopics = (
        query
        .order_by(forum_models.ForumTopic.date_created.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    allTopicsInDb = []
    for topic in allForumTopics:
        topicSchema = forum_schema.TopicInDb.model_validate(topic)
        topicSchema.user_username = topic.user.profile.username if topic.user else topic.admin.email_address
        topicSchema.user_fullname = topic.user.profile.fullname if topic.user else topic.admin.fullname
        topicSchema.user_profile_pic = topic.user.profile.profile_pic if topic.user else topic.admin.profile_pic
        topicSchema.comment_count = len(topic.answers)

        if not topicSchema.user_profile_pic:
            topicSchema.user_profile_pic = f"https://eu.ui-avatars.com/api/?name={topic.user.profile.fullname if topic.user else topic.admin.fullname}&size=250"

        allTopicsInDb.append(jsonable_encoder(topicSchema))

    # allTopicsInDb.reverse()

    return templates.TemplateResponse("/pages/forum/topics.html",
                                      {"request": request,
                                       "flash_message": flash_message,
                                       "current_user": current_user,
                                       "forum_topics": allTopicsInDb,
                                       "active_page": "forum",
                                       "category_values": category_values,
                                       "q": q,
                                       "page": page,
                                       "limit": limit,
                                       "total": total})


@router.post(path="/forum/topic/add", tags=["Admin"])
async def admin_add_forum_topic(request: Request, current_user=Depends(require_login), db: Session = Depends(get_db)):
    formData = await request.form()
    result=crud.add_forum_topic(db=db, request=request, formData=formData, current_user=current_user)
    if isinstance(result, RedirectResponse):
        return result
    return RedirectResponse(url="/admin/forum/topics", status_code=303)


@router.get("/forum/topics/{topic_id}/details", tags=["Admin"])
async def forum_topics_details(request: Request, topic_id: str, db: Session = Depends(get_db)):
    flash_message = request.session.pop("flash_message", None)
    current_user = await get_current_admin(request, db)
    if not current_user:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    topicInDb = db.query(forum_models.ForumTopic).filter_by(id=topic_id).first()

    topicSchema = forum_schema.TopicInDb.model_validate(topicInDb)
    topicSchema.user_username = topicInDb.user.profile.username if topicInDb.user else topicInDb.admin.email_address
    topicSchema.user_fullname = topicInDb.user.profile.fullname if topicInDb.user else topicInDb.admin.fullname
    # topicSchema.user_fullname = topicInDb.user.profile.fullname
    topicSchema.user_profile_pic = topicInDb.user.profile.profile_pic if topicInDb.user else topicInDb.admin.profile_pic
    # topicSchema.user_profile_pic = topicSchema.profile_picture
    topicSchema.comment_count = len(topicInDb.answers)

    if not topicSchema.user_profile_pic:
        topicSchema.user_profile_pic = f"https://eu.ui-avatars.com/api/?name={topicInDb.user.profile.fullname if topicInDb.user else topicInDb.admin.fullname}&size=250"

    return templates.TemplateResponse("/pages/forum/topic-details.html",
                                      {"request": request,
                                       "flash_message": flash_message,
                                       "current_user": current_user,
                                       "forum_topic": topicSchema,
                                       "active_page": "forum"})


@router.delete("/api/forum/topic", tags=["Admin"])
async def delete_forum_topics(request: Request, id: str, db: Session = Depends(get_db)):
    result = forum_crud.delete_topic(request, id, db)
    return result


# =======> Forum and community section end <=======

@router.get(path="/api/users/locations", tags=['Admin'])
def users_locations(db: Session = Depends(get_db)):
    usersInDb = db.query(auth_models.User).filter(
        auth_models.User.account_status == auth_schemas.AccountStatus.Enabled).all()
    locations = set([user.profile.address for user in usersInDb])
    return locations

@router.get(path="/shop/sell/items", tags=['Admin'])
def shop_sell_items(request: Request, db: Session = Depends(get_db), current_user=Depends(require_login),
                    page: int = Query(1, ge=1),
                    limit: int = Query(10, ge=1, le=50),
                    ):
    search = request.query_params.get("q")
    query = db.query(shop_models.ShopItem)

    if search:
        query = query.filter(
            or_(
                shop_models.ShopItem.title.ilike(f"%{search}%"),
                shop_models.ShopItem.brand.ilike(f"%{search}%"),
                shop_models.ShopItem.category.ilike(f"%{search}%"),
            )
        )

    total = query.count()

    offset = (page - 1) * limit

    ShopItemsDb = (
        query
        .order_by(shop_models.ShopItem.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return templates.TemplateResponse(
        "/pages/shop/all_shop_items.html",
        {
            "request": request,
            "ShopItemsDb": ShopItemsDb,
            "page": page,
            "limit": limit,
            "total": total,
            "search": search,
            "current_user": current_user,
        }
    )

from math import ceil
@router.get(path="/shop/sold/items", tags=['Admin'])
async def shop_sold_items(request: Request,db: Session = Depends(get_db),current_user=Depends(require_login),page: int = Query(1, ge=1),limit: int = Query(10, ge=1, le=50)):
    search = request.query_params.get("q")
    query = db.query(shop_models.Sales).join(
        shop_models.ShopItem,
        shop_models.Sales.item_id == shop_models.ShopItem.id
    )

    if search:
        query = query.filter(
            or_(
                shop_models.ShopItem.title.ilike(f"%{search}%"),
                shop_models.Sales.delivery_method.ilike(f"%{search}%"),
                shop_models.Sales.delivery_details.ilike(f"%{search}%"),
                shop_models.Sales.payment_method.ilike(f"%{search}%"),
            )
        )
    total = query.count()
    offset = (page - 1) * limit
    total_pages = ceil(total / limit)
    ShopItemsDb = (
        query
        .order_by(shop_models.Sales.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return templates.TemplateResponse(
        "/pages/shop/sold_items.html",
        {
            "request": request,
            "ShopItemsDb": ShopItemsDb,
            "items": [i.id for i in ShopItemsDb],
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "q": search,
            "current_user": current_user
        }
    )


# subscription management

@router.get(path="/subscription", tags=['Admin'])
def subscription_management(request: Request, db: Session = Depends(get_db), current_user=Depends(require_login)):
    SubscriptionInDb = db.query(subscription_model.UserSubscription).all()
    return templates.TemplateResponse("/pages/subscription/view_all.html", locals())


@router.get("/users-report", tags=['Admin'])
def user_reports(request: Request, db: Session = Depends(get_db, ), current_user=Depends(require_login),
                 user_id: str = Query(None), q: str = Query(None),page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    if user_id:
        crud.disabled_user(db=db, user_id=user_id, request=request)
        return RedirectResponse("/admin/users-report")
    flash_message = request.session.pop("flash_message", None)

    query = db.query(other_models.UserReport)

    if q:
        query = query.filter(
            or_(
                other_models.UserReport.reason.ilike(f"%{q}%")
            )
        )
    total = query.count()
    offset = (page - 1) * limit

    ReportInDb = (
        query
        .order_by(desc(other_models.UserReport.date_created))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return templates.TemplateResponse(
        "/pages/report-users.html",
        {
            "request": request,
            "current_user": current_user,
            "ReportInDb": ReportInDb,
            "flash_message": flash_message,
            "total": total,
            "page": page,
            "limit": limit,
            "q": q
        }
    )


@router.get("/shop/item/material", tags=['Admin'])
async def shop_item_materials(
        request: Request, db: Session = Depends(get_db), current_user=Depends(require_login),
        action: str = Query(None), material_id=Query(None),page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=50)
):
    if action == "delete" and material_id is not None:
        crud.delete_material(request, db, material_id)
        return RedirectResponse(url="/admin/shop/item/material", status_code=303)

    active_page = "material"
    flash_message = request.session.pop("flash_message", None)

    search_q = request.query_params.get("q")
    material_query = db.query(shop_model.ItemMaterial)

    if search_q:
        material_query = material_query.filter(
            shop_model.ItemMaterial.name.ilike(f"%{search_q}%")
        )

    total_materials = material_query.count()
    offset = (page - 1) * limit

    MaterialsInDb = (
        material_query
        .order_by(shop_model.ItemMaterial.date_created.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    MaterialsInDb_json = jsonable_encoder(MaterialsInDb)

    return templates.TemplateResponse(
        "/pages/shop/materials.html",
        {
            "request": request,
            "current_user": current_user,
            "MaterialsInDb": MaterialsInDb,
            "MaterialsInDb_json": MaterialsInDb_json,
            "active_page": active_page,
            "flash_message": flash_message,
            "page": page,
            "limit": limit,
            "total": total_materials
        }
    )


@router.post("/shop/item/material/{action}", tags=['Admin'])
async def shop_item_materials(action: str, request: Request, db: Session = Depends(get_db)):
    formData = await request.form()
    if action == "edit":
        crud.update_material(db=db, request=request, formData=formData)
    else:
        crud.add_material(request=request, db=db, formData=formData)
    return RedirectResponse(url="/admin/shop/item/material", status_code=303)


@router.get("/shop/item/{item_id}/search-suggestion", tags=['Admin'])
async def search_suggestion(item_id, request: Request, db: Session = Depends(get_db),
                            current_user=Depends(require_login),
                            action: str = Query(None), _id=Query(None)):
    if action == "delete" and _id is not None:
        crud.delete_search_suggestion_term(
            request=request,
            db=db,
            term_id=_id
        )
    flash_message = request.session.pop("flash_message", None)
    item_details = db.query(shop_model.ShopItem).filter(shop_model.ShopItem.id == item_id).first()
    SuggestionInDb = db.query(shop_model.SearchSuggestion).filter(shop_model.SearchSuggestion.item_id == item_id).all()
    return templates.TemplateResponse("/pages/shop/search_suggestion.html", locals())


@router.post(path="/shop/item/{item_id}/search-suggestion", tags=["Admin"])
async def search_suggestions(item_id, request: Request, db: Session = Depends(get_db),
                             current_user=Depends(require_login)):
    formData = await request.form()
    return crud.add_search_suggestion_term(
        item_id=item_id,
        request=request,
        db=db,
        formData=formData
    )


# In app
@router.get(path="/item/pickup-points", tags=['Admin'])
async def pickup_points(
        request: Request,
        point_id: Optional[str] = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        q: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user=Depends(require_login)
):
    if point_id:
        return crud.delete_pickup_point(db=db, request=request, point_id=point_id)

    flash_message = request.session.pop("flash_message", None)

    offset = (page - 1) * page_size

    pickupQuery = db.query(shop_model.DeliveryPickUpPoint)
    if q:
        pickupQuery = pickupQuery.filter(
            or_(
                shop_model.DeliveryPickUpPoint.address.ilike(f"%{q}%"),
                shop_model.DeliveryPickUpPoint.city.ilike(f"%{q}%")
            )
        )

    total = pickupQuery.count()
    total_pages = (total + page_size - 1) // page_size

    pickup_points = (
        pickupQuery
        .order_by(desc(shop_model.DeliveryPickUpPoint.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return templates.TemplateResponse(
        "/pages/in_app/pickup_points.html",
        {
            "request": request,
            "PickUpPoints": pickup_points,
            "flash_message": flash_message,
            "page": page,
            "limit": page_size,
            "total": total,
            "total_pages": total_pages,
            "current_user": current_user,
            "q": q
        }
    )

@router.post(path="/item/pickup-points", tags=['Admin'])
async def add_pickup_points(request: Request, point_id: Optional[str] = None, db: Session = Depends(get_db)):
    formData = await request.form()
    city = formData.get('city', '').strip()
    address = formData.get('address', '').strip()

    if not city:
        request.session["flash_message"] = {
            "type": "error",
            "message": "City is required!"
        }
        return RedirectResponse(url="/admin/item/pickup-points", status_code=303)

    if not address:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Address is required!"
        }
        return RedirectResponse(url="/admin/item/pickup-points", status_code=303)

    if point_id:
        return crud.update_pickup_point(formData=formData, db=db, point_id=point_id, request=request)

    return crud.add_pickup_point(formData=formData, db=db, request=request)

@router.get(path="/affiliated-management", tags=['Admin'])
async def get_affiliates(
        request: Request,
        affiliate_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user=Depends(require_login)
):
    if affiliate_id:
        affiliated_crud.admin_delete_affiliate(
            db=db,
            request=request,
            affiliate_id=affiliate_id
        )
    return affiliated_crud.admin_get_affiliated(
        db=db,
        request=request,
        current_user=current_user
    )


@router.post(path="/affiliated-management", tags=['Admin'])
async def affiliate_management(
        request: Request,
        affiliate_id: Optional[str] = None,
        db: Session = Depends(get_db)
):
    formData = await request.form()
    if affiliate_id:
        return affiliated_crud.admin_update_affiliate(
            request=request,
            formData=formData,
            db=db,
            affiliate_id=affiliate_id
        )

    return affiliated_crud.admin_add_partner_affiliate(
        request=request,
        formData=formData,
        db=db
    )

@router.get(path="/affiliate-rewards/{affiliate_id}", tags=['Admin'])
async def affiliate_reward(
        affiliate_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user=Depends(require_login)
):
    return affiliated_crud.admin_show_affiliate_rewards(
        db=db, affiliate_id=affiliate_id, request=request, current_user=current_user
    )


@router.post(path="/affiliate-rewards/{reward_id}/update", tags=['Admin'])
async def affiliate_reward(
        reward_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user=Depends(require_login)
):
    formData = await request.form()
    return affiliated_crud.admin_reward_status_update(
        db=db,
        request=request,
        reward_id=reward_id,
        formData=formData
    )


@router.get(path="/affiliate", tags=['Admin'])
async def affiliate(
        request: Request,
        db: Session = Depends(get_db),
        current_user=Depends(require_login)
):
    flash_message = request.session.pop("flash_message", None)

    return templates.TemplateResponse(
        "/pages/in_app/affiliated.html",
        {
            "request": request,
            "flash_message": flash_message,
            "current_user": current_user

        })
