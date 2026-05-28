from pydantic import BaseModel, PrivateAttr, Field, ConfigDict, EmailStr
import random
from datetime import date, datetime
from affiliated import services
from typing import Optional, List


class AddAffiliate(BaseModel):
    name: str
    code: str = Field(default_factory=lambda: str(services.generate_affiliate_code()))
    start_date: date
    end_date: date
    percentage: int
    is_active: bool = True
    description: str
    email: EmailStr


class AffiliateDetails(BaseModel):
    id: str
    code: str
    max_uses: int
    use_count: int

    model_config = ConfigDict(from_attributes=True)


class AffiliatePartner(BaseModel):
    id: str
    name: str
    logo: str
    description: str

    class Config:
        from_attributes = True


class AffiliateSlider(BaseModel):
    id: str
    image: str
    redirect_path:  Optional[str] = ""

    class Config:
        from_attributes = True

