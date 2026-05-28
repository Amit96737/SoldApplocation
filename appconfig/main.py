from typing import Dict
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dependency import get_db
from . import crud, schemas, models


router = APIRouter(
    prefix="/app-config",
    tags=["App Config"]
)


@router.get("", tags=["App Config"])
async def get_app_config(db: Session = Depends(get_db)):
    return crud.get_app_config(db)


@router.post("/payment-method", tags=["App Config"])
async def add_payment_method(data: schemas.PaymentMethodBase, db: Session = Depends(get_db)):
    return crud.add_payment_method(data, db)


@router.post("/language", tags=["App Config"])
async def add_language(data: schemas.LanguageBase, db: Session = Depends(get_db)):
    unique_id = str(uuid4())
    supportedLanguageModel = models.SupportedLanguage(
        id=unique_id,
        name=data.name,
        code=data.code,
        flag=data.flag
    )

    db.add(supportedLanguageModel)
    db.commit()
    db.refresh(supportedLanguageModel)


@router.post("/locale/translation", tags=["App Config"])
async def add_new_translation(data: Dict[str, dict[str, str]], db: Session = Depends(get_db)):
    return crud.add_translation(data, db)


@router.get("/locale/translation", tags=["App Config"])
async def translation(language_code: str, db: Session = Depends(get_db)):
    return crud.get_translation(language_code, db)


@router.post("/home-slider", tags=["App Config"])
async def home_slider(slider_data: schemas.AddSlider, db: Session = Depends(get_db)):
    return crud.add_home_slider(slider_data, db)


@router.get("/home-slider", tags=["App Config"])
async def home_slider(db: Session = Depends(get_db)):
    return crud.get_home_slider(db)


