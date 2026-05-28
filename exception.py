from typing import Any

from fastapi import HTTPException
from starlette import status

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


class UnicornException(Exception):
    def __init__(self, message: str, status_code: Any):
        self.message = message
        self.status_code = status_code



