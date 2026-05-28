from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependency import get_db
from auth.main import get_current_user
from auth.models import User
from affiliated import models, schemas, crud
from typing import List

router = APIRouter(
    prefix="/affiliate",
    tags=['Affiliate']
)


@router.get(path="/")
def get_user_affiliate(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return crud.user_affiliate_link(
        db=db,
        user=current_user
    )


@router.get(path="/validate-code/{code}", tags=['Affiliate'])
async def validate_affiliate_link(code: str, db: Session = Depends(get_db)):
    return crud.validate_affiliate_code(db=db, code=code)


@router.get(path="/club-deals")
async def get_sliders(db: Session = Depends(get_db)):
    partners = db.query(models.Partner).all()
    sliders = db.query(models.AffiliateSlider).filter(models.AffiliateSlider.enabled == True).all()
    return {
        "partner": [schemas.AffiliatePartner.from_orm(p) for p in partners],
        "sliders": [schemas.AffiliateSlider.from_orm(s) for s in sliders]
    }
