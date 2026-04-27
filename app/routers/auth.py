from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_current_user as deps_get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.models import User

router = APIRouter(tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthenticatedUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    region_name: Optional[str] = None
    is_active: bool
    full_name: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    region_name: Optional[str] = None
    user: AuthenticatedUserOut


def _user_to_payload(user: User) -> AuthenticatedUserOut:
    return AuthenticatedUserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        region_name=user.region_name,
        is_active=bool(user.is_active),
        full_name=user.display_name,
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return deps_get_current_user(request=request, db=db)


def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    return get_current_user(request=request, db=db)


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    user = require_auth(request=request, db=db)
    raw_role = (user.role or "").strip()
    if raw_role not in {"admin", "ADMIN"} and not raw_role.startswith("ADMIN_L"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative access is required.",
        )
    return user


@router.post("/api/auth/login", response_model=LoginResponse)
@router.post("/auth/login", response_model=LoginResponse, include_in_schema=False)
def login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == credentials.username.strip()).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری غیرفعال است.",
        )

    if not str(user.hashed_password).startswith("$2"):
        user.hashed_password = get_password_hash(credentials.password)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(
        user.username,
        role=user.role,
        region_name=user.region_name,
    )
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite="lax",
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        region_name=user.region_name,
        user=_user_to_payload(user),
    )


@router.get("/api/auth/me", response_model=AuthenticatedUserOut)
@router.get("/auth/me", response_model=AuthenticatedUserOut, include_in_schema=False)
def read_current_user(current_user: User = Depends(deps_get_current_user)):
    return _user_to_payload(current_user)


@router.post("/api/auth/logout")
@router.post("/auth/logout", include_in_schema=False)
def logout(response: Response):
    response.delete_cookie("session_token")
    return {"success": True}
