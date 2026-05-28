import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status

from dependency import get_db
from exception import UnicornException
from . import models, schemas
from auth.models import User
from auth.main import get_current_user

router = APIRouter(
    prefix="/cms",
)


@router.get("", tags=["Cms"])
async def get_cms(slug: str, db: Session = Depends(get_db),
                  ):
    cmsInDb = db.query(models.Cms).filter_by(slug=slug).first()

    if not cmsInDb:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="cms content with this slug not found")

    return schemas.CmsInDb(id=cmsInDb.id, slug=cmsInDb.slug, content=json.loads(str(cmsInDb.content)))
