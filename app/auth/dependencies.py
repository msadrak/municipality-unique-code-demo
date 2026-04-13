from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user as auth_get_current_user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = auth_get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user
