from fastapi import HTTPException
from others import models, schemas
from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request
from I18n.load_language import get_lang_content
from auth.models import User
from fastapi.responses import JSONResponse
from exception import UnicornException


def add_user_report(request: Request, data: schemas.CreateUserReport, current_user: User, db: Session):
    # lang = request.headers.get('X-language', 'en')
    # language_content = get_lang_content(lang)
    report_to_user = db.query(User).filter(User.id == str(data.report_to_id)).first()
    if not report_to_user:
        return JSONResponse(
            status_code=404,
            content={"report_to_id": "user does not exist."}
        )
    elif report_to_user.id == current_user.id:
        return JSONResponse(
            status_code=404,
            content={"report_to_id": "You can not report your self"}
        )

    report = models.UserReport(
        report_by_id=current_user.id,
        report_to_id=data.report_to_id,
        reason=data.reason,
        description=data.description
    )

    db.add(report)
    db.commit()
    db.refresh(report)
    return report




