import json
from typing import Optional

from pydantic import BaseModel, field_validator


class Cms(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class CmsInDb(BaseModel):
    id: Optional[str] = None
    slug: Optional[str] = ""
    content: Optional[dict] = ""

    class Config:
        from_attributes = True

    @field_validator('content', mode='before', check_fields=False)
    def parse_content(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
        return v
