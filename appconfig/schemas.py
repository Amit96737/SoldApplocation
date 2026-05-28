from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from pydantic.v1 import BaseSettings


class AppConfigInDb(BaseModel):
    app_name: Optional[str] = ""
    currency_symbol: Optional[str] = ""
    support_email: Optional[str] = ""
    support_number: Optional[str] = ""
    shipping_fee: float
    featured_dressing_price: Optional[float] = None
    seller_msg : Optional[str] = ""
    payment_methods: Optional[List[Any]] = []
    languages: Optional[List[Any]] = []

    class Config:
        from_attributes = True


class TranslationData(BaseModel):
    translations: Dict[str, str]


class AddSlider(BaseModel):
    redirect_path: Optional[str] = ""
    slider_image_url: Optional[str] = ""


class PaymentMethodBase(BaseModel):
    name: Optional[str] = ""
    icon: Optional[str] = ""


class LanguageBase(BaseModel):
    name: Optional[str] = ""
    code: Optional[str] = ""
    flag: Optional[str] = ""


class LanguageInDb(LanguageBase):
    status: Optional[bool] = False
    default: Optional[bool] = False

    class Config:
        from_attributes = True


class PaymentMethodInDb(PaymentMethodBase):
    id: Optional[str] = ""
    enabled: Optional[bool] = False

    class Config:
        from_attributes = True


class AppEnv(BaseSettings):
    debug: bool
    app_name: str
    currency_symbol: str
    shipping_fee: float
    featured_dressing_price: float = 0.0
    support_email: str
    support_number: str
    app_icon: str
    db_url: str
    session_middleware_key: str
    jwt_secret_key: str
    brevo_api_key: str
    cloudinary_api_key: str
    cloudinary_secret_key: str
    cloudinary_cloud_name: str
    onesignal_app_id: str
    onesignal_api_key: str
    ipinfo_secret_key: str
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_ENV: str
    seller_msg : str

    class Config:
        env_file = ".env"  # Specify the location of the .env file
