import json
import os
from uuid import uuid4

from dotenv import set_key
from sqlalchemy import desc
from sqlalchemy.orm import Session
from starlette import status

import main
from exception import UnicornException
from appconfig import models, schemas

TRANSLATIONS_DIR = "I18n"


def get_app_config(db: Session):
    appConfigSchema = schemas.AppConfigInDb.model_validate(main.app_env)
    paymentMethodsInDb = db.query(models.PaymentMethod).all()
    languagesInDb = db.query(models.SupportedLanguage).order_by(
        desc(getattr(models.SupportedLanguage, 'default'))).all()

    paymentMethods = [schemas.PaymentMethodInDb.model_validate(paymentMethod) for paymentMethod in
                      paymentMethodsInDb if
                      paymentMethod.enabled]

    appConfigSchema.payment_methods = paymentMethods
    language = [schemas.LanguageInDb.model_validate(language) for language in languagesInDb if language.status]
    appConfigSchema.languages = language

    return appConfigSchema


def add_payment_method(data: schemas.PaymentMethodBase, db: Session):
    unique_id = str(uuid4())
    paymentMethodModel = models.PaymentMethod(
        id=unique_id,
        name=data.name,
        icon=data.icon
    )

    db.add(paymentMethodModel)
    db.commit()
    db.refresh(paymentMethodModel)

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message="Payment method added successfully")


def add_translation(localization_data: dict, db: Session):
    for key, value in localization_data.items():
        language_key = key
        for lang in value:
            translation = value[lang]
            if len(translation) < 1:
                translation = language_key
            file_path = os.path.join(TRANSLATIONS_DIR, f"{lang}.json")
            if os.path.exists(file_path):
                with open(file_path, "r+", encoding="utf-8") as file:
                    existing_translations = json.load(file)
                    existing_translations.update({language_key: translation})
                    file.seek(0)
                    json.dump(existing_translations, file, ensure_ascii=False, indent=4)
                    file.truncate()
            else:
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump({}, file, ensure_ascii=False, indent=4)

    return {"message": "Translations added successfully"}


def get_translation(language_code: str, db: Session):
    file_path = os.path.join(TRANSLATIONS_DIR, f"{language_code}.json")
    if os.path.exists(file_path):
        with open(file_path, "r+", encoding="utf-8") as file:
            translations = json.load(file)
            file.seek(0)
            return translations
    else:
        return {}


def get_localization(translation_key: str, db: Session):
    localization_data = {}
    supportedLanguage = db.query(models.SupportedLanguage).all()
    language_code = [language.code for language in supportedLanguage]

    for code in language_code:
        file_path = os.path.join(TRANSLATIONS_DIR, f"{code}.json")
        if os.path.exists(file_path):
            with open(file_path, "r+", encoding="utf-8") as file:
                translations = json.load(file)
                file.seek(0)
                localization_data.update({code: translations.get(translation_key, '')})
        else:
            return {}

    return localization_data


def get_home_slider(db: Session):
    homeSliderInDb = db.query(models.HomeSlider).filter(
        models.HomeSlider.enabled == True
    ).all()
    return homeSliderInDb


def add_home_slider(slider_data: schemas.AddSlider, db: Session):
    unique_id = str(uuid4())

    sliderDataDict = slider_data.model_dump()
    sliderDataDict['id'] = unique_id
    sliderModel = models.HomeSlider(**sliderDataDict)

    db.add(sliderModel)
    db.commit()
    db.refresh(sliderModel)

    raise UnicornException(status_code=status.HTTP_200_OK,
                           message="Slider added successfully")


# Function to change and save an environment variable
def update_env(key: str, value: str):
    os.environ[key] = value
    set_key(".env", key, value)


