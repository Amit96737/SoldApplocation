from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Preferences(BaseModel):
    show_location: Optional[bool] = True
    show_notification: Optional[bool] = True
    holiday_mode: Optional[bool] = False
