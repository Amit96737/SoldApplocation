from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class AccountStatus(str, Enum):
    Disabled = 'disabled'
    Enabled = 'enabled'
    Suspended = 'suspended'
    Deleted = 'deleted'


class AuthProvider(str, Enum):
    Email = 'email'
    Google = 'google'
    Facebook = 'facebook'
    Apple = 'apple'


class CreateUser(BaseModel):
    email_address: Optional[str]
    password: Optional[str]
    fullname: Optional[str]
    nickname: Optional[str] = ""
    is_seller: Optional[bool] = False
    comapny_name: Optional[str] = None
    company_registration_num: Optional[str] = None
    auth_provider: Optional[AuthProvider] = AuthProvider.Email

    @field_validator('company_registration_num')
    @classmethod
    def validate_israeli_company_number(cls, value):
        if value:
            if not value.isdigit():
                raise ValueError("Company registration number must be numeric.")

            if not value.startswith("5"):
                raise ValueError("Company registration number must start with '5'.")

            if not cls.luhn_check(value):
                raise ValueError("Invalid Israeli company registration number (failed checksum).")

        return value


    @staticmethod
    def luhn_check(number: str) -> bool:
        digits = [int(d) for d in number]
        total = 0
        for i, digit in enumerate(digits[:-1]):
            if i % 2 == 0:
                add = digit * 1
            else:
                add = digit * 2
            if add > 9:
                add -= 9
            total += add
        check_digit = (10 - (total % 10)) % 10
        return check_digit == digits[-1]


class UserLogin(BaseModel):
    email_address: Optional[str] = "tester@gmail.com"
    password: Optional[str] = "tester123"


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
