"""
Authentication Router
=====================

Handles all authentication-related endpoints:
- Login/Logout
- Session management
- User registration
- User listing

Session tokens are stored in-memory (for development).
In production, use Redis or database-backed sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import secrets
import os

from app import models
from app.database import SessionLocal
from app.auth_utils import hash_password, verify_password, upgrade_hash_if_needed

router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Session Management (Simple in-memory for development) ---
# In production, use Redis or database-backed sessions
active_sessions = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_session(user_id: int) -> str:
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    active_sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=8)
    }
    return token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """Get current user from session token"""
    token = request.cookies.get("session_token")
    if not token or token not in active_sessions:
        return None
    
    session = active_sessions[token]
    if datetime.utcnow() > session["expires_at"]:
        del active_sessions[token]
        return None
    
    return db.query(models.User).filter(models.User.id == session["user_id"]).first()


def require_auth(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Require authentication - raise exception if not logged in"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user


def require_admin(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Require admin role"""
    user = require_auth(request, db)
    if user.role != "admin":
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
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login and create session"""
    user = db.query(models.User).filter(models.User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="حساب کاربری غیرفعال است")
    
    # Upgrade legacy SHA-256 hash to Argon2 on successful login
    new_hash = upgrade_hash_if_needed(data.password, user.password_hash)
    if new_hash:
        user.password_hash = new_hash
        db.commit()
    
    token = create_session(user.id)
    
    # Secure cookie settings
    is_production = os.getenv("PRODUCTION", "false").lower() == "true"
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=is_production,
        max_age=8 * 60 * 60,  # 8 hours
        samesite="lax"
    )
    
    return {
        "status": "success",
        "message": "ورود موفق",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role
        }
    }


@router.post("/logout")
def logout(response: Response, request: Request):
    """Logout and destroy session"""
    token = request.cookies.get("session_token")
    if token and token in active_sessions:
        del active_sessions[token]
    
    response.delete_cookie("session_token")
    return {"status": "success", "message": "خروج موفق"}


@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    """Get current user info"""
    user = get_current_user(request, db)
    if not user:
        return {"authenticated": False}
    
    # Get default org units
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
            "default_section": section_info
        }
    }


@router.post("/register")
def register_user(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register new user (admin only, or first user becomes admin)"""
    user_count = db.query(models.User).count()
    
    if user_count > 0:
        current_user = get_current_user(request, db)
        if not current_user or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="فقط ادمین می‌تواند کاربر جدید ایجاد کند")
    
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
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "status": "success",
        "message": "کاربر با موفقیت ایجاد شد",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role
        }
    }


@router.get("/users")
def list_users(request: Request, db: Session = Depends(get_db)):
    """List all users (admin only)"""
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
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
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    }
