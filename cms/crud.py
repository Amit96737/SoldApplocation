import json
from uuid import uuid4

from sqlalchemy.orm import Session
from starlette import status

from cms import models, schemas
from exception import UnicornException



def get_cms(slug: str, db: Session):
    cmsInDb = db.query(models.Cms).filter(models.Cms.slug == slug).first()
    if cmsInDb:
        return schemas.CmsInDb(
            id=cmsInDb.id,
            slug=cmsInDb.slug,
            content=json.loads(str(cmsInDb.content))
        )
    else:
        raise UnicornException(status_code=status.HTTP_404_NOT_FOUND,
                               message="Cms with this slug not found")


def update_cms(cms_data: schemas.Cms, lang: str, slug: str, db: Session):
    cmsInDb = db.query(models.Cms).filter(models.Cms.slug == slug).first()
    if cmsInDb:
        cms_content = json.loads(str(cmsInDb.content))
        cms_content[lang] = {
            "title": cms_data.title or cms_content[lang].get("title"),
            "content": cms_data.content or cms_content[lang].get("content"),
        }
        cmsInDb.content = json.dumps(cms_content)
        db.commit()
    else:
        unique_id = str(uuid4())
        content = {
            f"{lang}": {
                "title": cms_data.title,
                "content": cms_data.content
            }
        }
        cms_model = models.Cms(
            id=unique_id,
            slug=slug,
            content=json.dumps(content),
        )

        db.add(cms_model)
        db.commit()
        db.refresh(cms_model)

        raise UnicornException(status_code=status.HTTP_200_OK,
                               message="Cms updated successfully")
