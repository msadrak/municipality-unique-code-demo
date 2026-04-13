"""
Authentication Router
=====================

Handles all authentication-related endpoints:
- Login/Logout
- Session management (Redis-backed)
- User registration
- User listing

Session tokens are stored in Redis with a 1-hour TTL.
"""
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal, get_db
from app.auth_utils import hash_password, verify_password, upgrade_hash_if_needed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Redis Client
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = 60 * 60  # 1 hour

redis_client: redis.Redis = redis.from_url(
    REDIS_URL, decode_responses=True
)
redis_client.ping()
logger.info("Redis connection established for session management")


# ---------------------------------------------------------------------------
# Password Policy
# ---------------------------------------------------------------------------

def validate_password_policy(password: str) -> None:
    """Validate password meets enterprise security requirements."""
    if len(password) < 10:
        raise HTTPException(status_code=400, detail="رمز عبور باید حداقل ۱۰ کاراکتر باشد")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="رمز عبور باید حداقل یک حرف بزرگ داشته باشد")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="رمز عبور باید حداقل یک حرف کوچک داشته باشد")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="رمز عبور باید حداقل یک عدد داشته باشد")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="رمز عبور باید حداقل یک کاراکتر خاص داشته باشد")


# ---------------------------------------------------------------------------
# Account Lockout
# ---------------------------------------------------------------------------

def check_account_locked(user: models.User) -> None:
    """Check if account is locked and raise exception if so."""
    if user.locked_until and user.locked_until.replace(tzinfo=None) > datetime.utcnow():
        logger.warning(
            "ACCOUNT_LOCKED | user_id=%s username=%s locked_until=%s",
            user.id,
            user.username,
            user.locked_until.isoformat(),
        )
        raise HTTPException(status_code=403, detail="حساب کاربری قفل شده است. لطفاً بعداً تلاش کنید")


def handle_failed_login(user: models.User, db: Session, client_ip: str) -> None:
    """Increment failed attempts and lock account if threshold reached."""
    user.failed_attempts = (user.failed_attempts or 0) + 1
    
    if user.failed_attempts >= 3:
        user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        logger.warning(
            "ACCOUNT_LOCKED | user_id=%s username=%s ip=%s failed_attempts=%s",
            user.id,
            user.username,
            client_ip,
            user.failed_attempts,
        )
    else:
        logger.warning(
            "LOGIN_FAILED | user_id=%s username=%s ip=%s failed_attempts=%s",
            user.id,
            user.username,
            client_ip,
            user.failed_attempts,
        )
    
    db.commit()


def reset_failed_attempts(user: models.User, db: Session) -> None:
    """Reset failed login attempts on successful login."""
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()


# ---------------------------------------------------------------------------
# Session helpers (Redis-backed)
# ---------------------------------------------------------------------------

def _session_key(token: str) -> str:
    """Return the Redis key used to store a session."""
    return f"session:{token}"


def create_session(user_id: int) -> str:
    """Create a new session token and persist it in Redis."""
    token = secrets.token_urlsafe(32)
    session_data = json.dumps({
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
    })
    try:
        redis_client.setex(_session_key(token), SESSION_TTL_SECONDS, session_data)
    except redis.RedisError as exc:
        logger.error("Failed to create session in Redis: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="سرویس نشست‌ها در دسترس نیست. لطفاً دوباره تلاش کنید.",
        ) from exc
    return token


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[models.User]:
    """Get current user from Redis session token."""
    token = request.cookies.get("session_token")
    if not token:
        return None

    try:
        raw = redis_client.get(_session_key(token))
    except redis.RedisError as exc:
        logger.warning("Redis read error during session lookup: %s", exc)
        return None

    if raw is None:
        return None

    try:
        session = json.loads(raw)
    except JSONDecodeError:
        logger.warning("Malformed session payload for token=%s", token[:8])
        return None

    user_id = session.get("user_id") if isinstance(session, dict) else None
    if not user_id:
        logger.warning("Session payload missing user_id for token=%s", token[:8])
        return None

    return (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )


def require_auth(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    """Require authentication — raise exception if not logged in."""
    user = get_current_user(request, db)
    if not user:
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "UNAUTHORIZED_ACCESS | ip=%s endpoint=%s",
            client_ip,
            request.url.path,
        )
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user


def require_admin(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    """Require admin role."""
    user = require_auth(request, db)
    if user.role != "admin":
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "UNAUTHORIZED_ACCESS | user_id=%s username=%s ip=%s endpoint=%s role=%s",
            user.id,
            user.username,
            client_ip,
            request.url.path,
            user.role,
        )
        raise HTTPException(status_code=403, detail="دسترسی فقط برای ادمین")
    return user


# --- Request Models ---

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "user"
    default_zone_id: Optional[int] = None
    default_dept_id: Optional[int] = None
    default_section_id: Optional[int] = None


# --- Endpoints ---

@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login and create session."""
    client_ip = request.client.host if request.client else "unknown"
    
    user = db.query(models.User).filter(models.User.username == data.username).first()
    
    if not user:
        logger.warning(
            "LOGIN_FAILED | username=%s ip=%s endpoint=/auth/login reason=user_not_found",
            data.username,
            client_ip,
        )
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    
    check_account_locked(user)
    
    if not verify_password(data.password, user.password_hash):
        handle_failed_login(user, db, client_ip)
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")

    if not user.is_active:
        logger.warning(
            "LOGIN_FAILED | user_id=%s username=%s ip=%s reason=inactive_account",
            user.id,
            user.username,
            client_ip,
        )
        raise HTTPException(status_code=401, detail="حساب کاربری غیرفعال است")

    reset_failed_attempts(user, db)

    new_hash = upgrade_hash_if_needed(data.password, user.password_hash)
    if new_hash:
        user.password_hash = new_hash
        db.commit()

    token = create_session(user.id)

    is_production = os.getenv("PRODUCTION", "false").lower() == "true"
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=is_production,
        max_age=SESSION_TTL_SECONDS,
        samesite="lax",
    )

    logger.info(
        "LOGIN_SUCCESS | user_id=%s username=%s ip=%s endpoint=/auth/login",
        user.id,
        user.username,
        client_ip,
    )

    return {
        "status": "success",
        "message": "ورود موفق",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.post("/logout")
def logout(response: Response, request: Request):
    """Logout and destroy session."""
    client_ip = request.client.host if request.client else "unknown"
    token = request.cookies.get("session_token")
    
    user_id = None
    if token:
        try:
            raw = redis_client.get(_session_key(token))
            if raw:
                session = json.loads(raw)
                user_id = session.get("user_id")
            redis_client.delete(_session_key(token))
        except redis.RedisError as exc:
            logger.warning("Redis delete error during logout: %s", exc)

    logger.info(
        "LOGOUT | user_id=%s ip=%s endpoint=/auth/logout",
        user_id or "unknown",
        client_ip,
    )

    response.delete_cookie("session_token")
    return {"status": "success", "message": "خروج موفق"}


@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    """Get current user info."""
    user = get_current_user(request, db)
    if not user:
        return {"authenticated": False}

    zone_info = dept_info = section_info = None
    if user.default_zone_id:
        zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == user.default_zone_id).first()
        zone_info = {"id": zone.id, "code": zone.code, "title": zone.title} if zone else None
    if user.default_dept_id:
        dept = db.query(models.OrgUnit).filter(models.OrgUnit.id == user.default_dept_id).first()
        dept_info = {"id": dept.id, "code": dept.code, "title": dept.title} if dept else None
    if user.default_section_id:
        section = db.query(models.OrgUnit).filter(models.OrgUnit.id == user.default_section_id).first()
        section_info = {"id": section.id, "code": section.code, "title": section.title} if section else None

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "default_zone": zone_info,
            "default_dept": dept_info,
            "default_section": section_info,
        },
    }


@router.post("/register")
def register_user(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register new user (admin only, or first user becomes admin)."""
    client_ip = request.client.host if request.client else "unknown"
    user_count = db.query(models.User).count()

    if user_count > 0:
        current_user = get_current_user(request, db)
        if not current_user or current_user.role != "admin":
            logger.warning(
                "UNAUTHORIZED_ACCESS | ip=%s endpoint=/auth/register reason=not_admin",
                client_ip,
            )
            raise HTTPException(status_code=403, detail="فقط ادمین می‌تواند کاربر جدید ایجاد کند")

    validate_password_policy(data.password)

    existing = db.query(models.User).filter(models.User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="نام کاربری قبلاً استفاده شده")

    user = models.User(
        username=data.username,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role="admin" if user_count == 0 else data.role,
        default_zone_id=data.default_zone_id,
        default_dept_id=data.default_dept_id,
        default_section_id=data.default_section_id,
        is_active=True,
        failed_attempts=0,
        locked_until=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(
        "USER_CREATED | user_id=%s username=%s ip=%s endpoint=/auth/register",
        user.id,
        user.username,
        client_ip,
    )

    return {
        "status": "success",
        "message": "کاربر با موفقیت ایجاد شد",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.get("/users")
def list_users(request: Request, db: Session = Depends(get_db)):
    """List all users (admin only)."""
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            "UNAUTHORIZED_ACCESS | user_id=%s ip=%s endpoint=/auth/users reason=not_admin",
            current_user.id if current_user else "unknown",
            client_ip,
        )
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")

    users = db.query(models.User).all()
    return {
        "count": len(users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }
