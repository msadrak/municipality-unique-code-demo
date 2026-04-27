from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials were not provided or are invalid.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "").strip()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token

    cookie_token = request.cookies.get("session_token")
    if cookie_token:
        return cookie_token

    raise _credentials_exception()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(request)

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise _credentials_exception() from exc

    username = str(payload.get("sub") or "").strip()
    if not username:
        raise _credentials_exception()

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise _credentials_exception()

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    allowed = {role.upper() for role in allowed_roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user

    return dependency
