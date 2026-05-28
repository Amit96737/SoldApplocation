from pydantic import BaseModel
from uuid import UUID


class CreateUserReport(BaseModel):
    reason: str
    report_to_id: UUID
    description: str

    class Config:
        from_attributes = True


