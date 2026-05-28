# Dependency
from datetime import datetime

from fastapi import Depends
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from auth import crud as auth_crud
from auth.schemas import AccountStatus
from constants import SECRET_KEY, ALGORITHM, oauth2_scheme
from database import SessionLocal
from exception import credentials_exception
import main


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_env():
    return main.app_env


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email_address: str = payload.get("sub")
        if email_address is None:
            raise credentials_exception
        token_data = email_address
    except JWTError:
        raise credentials_exception
    user = auth_crud.get_user(token_data, db)

    if user is None:
        raise credentials_exception

    user.last_seen = datetime.utcnow()
    db.commit()

    if user.account_status != AccountStatus.Enabled:
        raise credentials_exception

    return user


