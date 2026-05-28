import logging
from affiliated import models, schemas, services
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import Request
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from auth import models as auth_models
from datetime import datetime
from exception import UnicornException
from starlette import status
from subscription import models as subscription_models, crud as subscription_crud
from sqlalchemy import or_, and_, exists
from decimal import Decimal
import cloudinary
from cloudinary.uploader import upload
from datetime import datetime, date

templates = Jinja2Templates(directory="templates")


def admin_get_affiliated(db: Session, request: Request, current_user):
    flash_message = request.session.pop("flash_message", None)
    AffiliatesInDb = (
        db.query(models.Affiliate).filter(models.Affiliate.user != None).order_by(desc(models.Affiliate.date_created))
        .all()
    )

    PartnersInDb = db.query(models.Affiliate).filter(models.Affiliate.partner != None).order_by(desc(models.Affiliate.date_created)).all()

    return templates.TemplateResponse(
        "/pages/in_app/affiliated_management.html",
        {
            "request": request,
            "AffiliatesInDb": AffiliatesInDb,
            "PartnersInDb": PartnersInDb,
            "flash_message": flash_message,
            "current_user": current_user,
            "active_page": "affiliated-management"
        }
    )

def admin_add_partner_affiliate(request: Request, formData, db: Session):
    name = formData.get("name", "").strip()

    start_date_str = formData.get("start_date")
    end_date_str = formData.get("end_date")

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    if not name:
        request.session["flash_message"] = {
            "type": "error",
            "message": "Name is required!"
        }
        return RedirectResponse(url="/admin/affiliated-management", status_code=303)

    if end_date < start_date or end_date < date.today():
        request.session["flash_message"] = {
            "type": "error",
            "message": "Please correct expiry date"
        }
        return RedirectResponse(url="/admin/affiliated-management", status_code=303)

    uploaded_image_url = cloudinary.uploader.upload(formData.get('logo').file, folder="Sold/Partner")
    formData = schemas.AddAffiliate.model_validate(formData)

    partner = models.Partner(
        name=name,
        email=formData.email,
        description=formData.description,
        logo=uploaded_image_url.get('url')
    )

    db.add(partner)
    db.commit()

    Affiliate = models.Affiliate(
        code=formData.code,
        start_date=formData.start_date,
        end_date=formData.end_date,
        percentage=formData.percentage,
        partner_id=partner.id
    )

    db.add(Affiliate)
    db.commit()

    request.session["flash_message"] = {
        "type": "success",
        "message": f"Partner added successfully."
    }
    return RedirectResponse(url=f"/admin/affiliated-management", status_code=303)


def admin_update_affiliate(request: Request, formData, db: Session, affiliate_id):
    affiliate = db.query(models.Affiliate).filter(models.Affiliate.id == affiliate_id).first()
    formData = schemas.AddAffiliate.model_validate(formData)
    affiliate.title = formData.title
    affiliate.start_date = formData.start_date
    affiliate.end_date = formData.end_date
    affiliate.percentage = formData.percentage
    affiliate.is_active = formData.is_active
    if formData.user_id:
        affiliate.user_id = formData.user_id
    db.commit()
    request.session["flash_message"] = {
        "type": "success",
        "message": f"Affiliate link update successfully."
    }
    return RedirectResponse(url=f"/admin/affiliated-management", status_code=303)


def admin_delete_affiliate(request: Request, db: Session, affiliate_id):
    try:
        affiliate = db.query(models.Affiliate).filter(models.Affiliate.id == affiliate_id).first()
        db.delete(affiliate)
        db.commit()
        request.session["flash_message"] = {
            "type": "success",
            "message": f"Affiliate link {affiliate.code} deleted successfully."
        }
    except Exception as e:
        print(e)
    return True


def admin_show_affiliate_rewards(db: Session, affiliate_id: str, request: Request, current_user):
    flash_message = request.session.pop("flash_message", None)
    Affiliate = db.query(models.Affiliate).filter(models.Affiliate.id == affiliate_id).first()
    AffiliateRewards = db.query(models.AffiliateReward).filter(models.AffiliateReward.affiliate_id == Affiliate.id)
    return templates.TemplateResponse(
        "/pages/in_app/affiliate_rewards.html",
        {
            "request": request,
            "flash_message": flash_message,
            "current_user": current_user,
            "affiliate": Affiliate,
            "affiliate_rewards": AffiliateRewards
        }
    )


def admin_reward_status_update(db: Session, reward_id: str, request: Request, formData):
    AffiliateRewards = db.query(models.AffiliateReward).filter(models.AffiliateReward.id == reward_id).first()
    AffiliateRewards.status = formData.get("status", AffiliateRewards.status)
    db.commit()
    request.session["flash_message"] = {
        "type": "success",
        "message": f"Reward status update successfully."
    }
    return RedirectResponse(url=f"/admin/affiliate-rewards/{AffiliateRewards.affiliate_id}", status_code=303)


def user_affiliate_link(user, db: Session):
    affiliate = db.query(models.Affiliate).filter(models.Affiliate.user_id == user.id).first()
    if not affiliate:
        affiliate = models.Affiliate(
            code=services.generate_affiliate_code(),
            start_date=datetime.now().date(),
            user_id=user.id
        )
        db.add(affiliate)
        db.commit()
    # rewards = affiliate.rewards
    affiliate_details = schemas.AffiliateDetails.model_validate(affiliate).model_dump()
    affiliate_details['subscription'] = 0
    affiliate_details['com_generated'] = 0
    affiliate_details['com_paid'] = 0
    affiliate_details['com_pending'] = 0
    return affiliate_details


def is_user_subscription_active(db: Session, user_id: str) -> bool:
    return db.query(subscription_models.UserSubscription).join(subscription_models.SubscriptionPlan).filter(
        subscription_models.UserSubscription.user_id == user_id,
        or_(
            subscription_models.UserSubscription.expire_on is None,
            subscription_models.UserSubscription.expire_on > datetime.utcnow()
        )
    ).first() is not None


def reward_of_affiliate_code(db: Session, code: str, current_user_id, subscription_id, plain_price):
    AffiliateInDb = db.query(models.Affiliate).filter(models.Affiliate.code == code,
                                                      models.Affiliate.is_active == True).first()
    if not AffiliateInDb:
        return True

    NewUserSubscription = db.query(
        exists().where(and_(
            subscription_models.UserSubscription.user_id == current_user_id,
            subscription_models.UserSubscription.id != subscription_id
        ))
    ).scalar()

    def add_reward(reward, reward_amount):
        Reward = models.AffiliateReward(
            referrer_id=current_user_id,
            affiliate_id=AffiliateInDb.id,
            subscription_id=subscription_id,
            reward_type=reward,
            status="pending",
            amount=reward_amount
        )
        db.add(Reward)
        db.commit()
        logging.info(f"reward added successfully type--{reward} -- amount -- {reward_amount}")

    if not NewUserSubscription and AffiliateInDb.user_id:
        if is_user_subscription_active(
                db=db,
                user_id=AffiliateInDb.user_id
        ):
            reward_type = "money"
        else:
            reward_type = "package"

        amount = round(plain_price * (Decimal(AffiliateInDb.percentage) / Decimal(100)), 2)
        add_reward(reward_type, amount)

    elif not NewUserSubscription and not AffiliateInDb.user_id:
        amount = round(plain_price * (Decimal(AffiliateInDb.percentage) / Decimal(100)), 2)
        add_reward("money", amount)
    else:
        logging.debug("reward not add due to condition not match.")


def validate_affiliate_code(db: Session, code: str):
    AffiliateInDb = db.query(models.Affiliate).filter(
        models.Affiliate.code == code
    ).first()

    if not AffiliateInDb:
        return UnicornException(
            message="No matching code found in the record.", status_code=status.HTTP_404_NOT_FOUND
        )
    elif AffiliateInDb.is_active is False:
        return UnicornException(
            message="Code has been expired.", status_code=status.HTTP_400_BAD_REQUEST
        )
    return {
        "status_code": 200,
        "message": "validated successfully."
    }

