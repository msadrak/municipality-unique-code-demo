from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import hashlib
import pandas as pd
import secrets
import os
from datetime import datetime, timedelta

# Import internal modules
from app import models, schemas, crud
from app.database import SessionLocal, engine
from app.auth_utils import hash_password, verify_password, upgrade_hash_if_needed
from sqlalchemy import or_

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Municipality Action Portal")

# --- CORS Configuration ---
# In production, set ALLOWED_ORIGINS environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# --- Mount React Build Static Files ---
# Serve React app assets from figma_export/build
REACT_BUILD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "figma_export", "build")
if os.path.exists(REACT_BUILD_PATH):
    app.mount("/react-assets", StaticFiles(directory=os.path.join(REACT_BUILD_PATH, "assets")), name="react-assets")

# --- Session Management (Simple in-memory for development) ---
# In production, use Redis or database-backed sessions
active_sessions = {}

# Password hashing functions are now imported from app.auth_utils
# They use Argon2 with gradual migration from SHA-256

def create_session(user_id: int) -> str:
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    active_sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=8)
    }
    return token

def get_current_user(request: Request, db: Session = Depends(lambda: next(SessionLocal()))) -> Optional[models.User]:
    """Get current user from session token"""
    token = request.cookies.get("session_token")
    if not token or token not in active_sessions:
        return None
    
    session = active_sessions[token]
    if datetime.utcnow() > session["expires_at"]:
        del active_sessions[token]
        return None
    
    return db.query(models.User).filter(models.User.id == session["user_id"]).first()

def require_auth(request: Request, db: Session = Depends(lambda: next(SessionLocal()))) -> models.User:
    """Require authentication - raise exception if not logged in"""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user

def require_admin(request: Request, db: Session = Depends(lambda: next(SessionLocal()))) -> models.User:
    """Require admin role"""
    user = require_auth(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="دسترسی فقط برای ادمین")
    return user

# Excel file path
EXCEL_FILE = "combined_output_version_2.xlsx"
ZONE_FILTER = 20  # Focus on Zone 20 only

# Cache for sheet names (loaded once at startup)
_sheet_names_cache = None

def get_sheet_names():
    global _sheet_names_cache
    if _sheet_names_cache is None:
        xl = pd.ExcelFile(EXCEL_FILE)
        _sheet_names_cache = xl.sheet_names
    return _sheet_names_cache

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def safe_str(val, default=""):
    """Convert value to string, returning default for NaN/None values"""
    if pd.isna(val):
        return default
    return str(val)

def clean_request_id(req):
    """Clean request ID - strip spaces, handle comma-separated values"""
    if pd.isna(req):
        return None
    req_str = str(req).strip()
    # Remove extra internal spaces
    req_str = ' '.join(req_str.split())
    return req_str if req_str else None

# --- PORTAL API ENDPOINTS ---

# --- AUTH ENDPOINTS ---

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

@app.post("/auth/login")
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
    # In production (HTTPS), set secure=True via PRODUCTION env var
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

@app.post("/auth/logout")
def logout(response: Response, request: Request):
    """Logout and destroy session"""
    token = request.cookies.get("session_token")
    if token and token in active_sessions:
        del active_sessions[token]
    
    response.delete_cookie("session_token")
    return {"status": "success", "message": "خروج موفق"}

@app.get("/auth/me")
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

@app.post("/auth/register")
def register_user(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register new user (admin only, or first user becomes admin)"""
    # Check if there are any users (first user becomes admin)
    user_count = db.query(models.User).count()
    
    if user_count > 0:
        # Require admin auth for subsequent registrations
        current_user = get_current_user(request, db)
        if not current_user or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="فقط ادمین می‌تواند کاربر جدید ایجاد کند")
    
    # Check if username exists
    existing = db.query(models.User).filter(models.User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="نام کاربری قبلاً استفاده شده")
    
    # Create user
    user = models.User(
        username=data.username,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role="admin" if user_count == 0 else data.role,  # First user is admin
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

@app.get("/auth/users")
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


# --- ADMIN API ENDPOINTS ---

class RejectRequest(BaseModel):
    reason: str

@app.get("/admin/transactions")
def admin_get_transactions(
    request: Request,
    status: str = "",
    search: str = "",
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get all transactions with filters (admin only)"""
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    query = db.query(models.Transaction)
    
    if status:
        query = query.filter(models.Transaction.status == status)
    if search:
        query = query.filter(
            or_(
                models.Transaction.unique_code.contains(search),
                models.Transaction.beneficiary_name.contains(search)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Get stats
    stats = {
        "total": db.query(models.Transaction).count(),
        "pending": db.query(models.Transaction).filter(models.Transaction.status == "pending").count(),
        "approved": db.query(models.Transaction).filter(models.Transaction.status == "approved").count(),
        "rejected": db.query(models.Transaction).filter(models.Transaction.status == "rejected").count(),
    }
    
    # Pagination
    offset = (page - 1) * limit
    transactions = query.order_by(models.Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for t in transactions:
        zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.zone_id).first() if t.zone_id else None
        result.append({
            "id": t.id,
            "unique_code": t.unique_code,
            "beneficiary_name": t.beneficiary_name,
            "amount": t.amount,
            "status": t.status,
            "zone_title": zone.title if zone else "-",
            "created_at": t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None
        })
    
    return {
        "transactions": result,
        "total": total,
        "page": page,
        "limit": limit,
        "stats": stats
    }

@app.get("/admin/transactions/{transaction_id}")
def admin_get_transaction_detail(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    """Get single transaction detail (admin only)"""
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
    
    # Get related entities
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.zone_id).first() if t.zone_id else None
    dept = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.department_id).first() if t.department_id else None
    section = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.section_id).first() if t.section_id else None
    budget = db.query(models.BudgetItem).filter(models.BudgetItem.id == t.budget_item_id).first() if t.budget_item_id else None
    event = db.query(models.FinancialEventRef).filter(models.FinancialEventRef.id == t.financial_event_id).first() if t.financial_event_id else None
    created_by = db.query(models.User).filter(models.User.id == t.created_by_id).first() if t.created_by_id else None
    reviewed_by = db.query(models.User).filter(models.User.id == t.reviewed_by_id).first() if t.reviewed_by_id else None
    
    return {
        "id": t.id,
        "unique_code": t.unique_code,
        "status": t.status,
        "beneficiary_name": t.beneficiary_name,
        "amount": t.amount,
        "contract_number": t.contract_number,
        "special_activity": t.special_activity,
        "description": t.description,
        "zone_title": zone.title if zone else "-",
        "dept_title": dept.title if dept else "-",
        "section_title": section.title if section else "-",
        "budget_code": budget.budget_code if budget else "-",
        "budget_description": budget.description if budget else "-",
        "financial_event_title": event.title if event else "-",
        "created_by_name": created_by.full_name if created_by else "-",
        "reviewed_by_name": reviewed_by.full_name if reviewed_by else None,
        "rejection_reason": t.rejection_reason,
        "created_at": t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None,
        "reviewed_at": t.reviewed_at.strftime("%Y/%m/%d %H:%M") if t.reviewed_at else None
    }

@app.post("/admin/transactions/{transaction_id}/approve")
def admin_approve_transaction(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    """
    تایید تراکنش با گردش کار ۴ سطحی
    
    هر ادمین فقط می‌تواند تراکنش‌های سطح خود را تایید کند:
    - ADMIN_L1 می‌تواند PENDING_L1 را به PENDING_L2 ببرد
    - ADMIN_L2 می‌تواند PENDING_L2 را به PENDING_L3 ببرد
    - ADMIN_L3 می‌تواند PENDING_L3 را به PENDING_L4 ببرد
    - ADMIN_L4 می‌تواند PENDING_L4 را به APPROVED ببرد
    """
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    # بررسی اینکه کاربر ادمین است
    if not current_user.role.startswith("ADMIN_L") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
    
    # نقشه گردش کار
    workflow_map = {
        "PENDING_L1": {"next_status": "PENDING_L2", "required_role": "ADMIN_L1", "required_level": 1},
        "PENDING_L2": {"next_status": "PENDING_L3", "required_role": "ADMIN_L2", "required_level": 2},
        "PENDING_L3": {"next_status": "PENDING_L4", "required_role": "ADMIN_L3", "required_level": 3},
        "PENDING_L4": {"next_status": "APPROVED", "required_role": "ADMIN_L4", "required_level": 4},
        # سازگاری با وضعیت قدیمی
        "pending": {"next_status": "APPROVED", "required_role": "admin", "required_level": 1},
    }
    
    current_status = t.status
    if current_status not in workflow_map:
        raise HTTPException(status_code=400, detail=f"تراکنش در وضعیت {current_status} قابل تایید نیست")
    
    workflow = workflow_map[current_status]
    
    # بررسی سطح دسترسی (برای سازگاری، admin قدیمی همه کارها را می‌تواند انجام دهد)
    if current_user.role != "admin":
        if current_user.role != workflow["required_role"]:
            raise HTTPException(
                status_code=403, 
                detail=f"شما سطح {current_user.role} هستید ولی این تراکنش نیاز به {workflow['required_role']} دارد"
            )
    
    previous_status = t.status
    new_status = workflow["next_status"]
    admin_level = workflow["required_level"]
    
    # فقط در تایید نهایی بودجه را کم کنیم
    if new_status == "APPROVED" and t.budget_item_id:
        budget = db.query(models.BudgetItem).filter(models.BudgetItem.id == t.budget_item_id).first()
        if budget:
            if budget.remaining_budget is None:
                budget.remaining_budget = (budget.allocated_1403 or 0) - (t.amount or 0)
            else:
                budget.remaining_budget -= (t.amount or 0)
            budget.reserved_amount = (budget.reserved_amount or 0) - (t.amount or 0)
            budget.spent_1403 = (budget.spent_1403 or 0) + (t.amount or 0)
    
    # بروزرسانی تراکنش
    t.status = new_status
    t.current_approval_level = admin_level
    t.reviewed_by_id = current_user.id
    t.reviewed_at = datetime.utcnow()
    
    # ثبت در تاریخچه گردش کار
    workflow_log = models.WorkflowLog(
        transaction_id=t.id,
        admin_id=current_user.id,
        admin_level=admin_level,
        action="APPROVE",
        comment=None,
        previous_status=previous_status,
        new_status=new_status
    )
    db.add(workflow_log)
    db.commit()
    
    return {
        "status": "success", 
        "message": f"تراکنش تایید شد و به وضعیت {new_status} رفت",
        "new_status": new_status,
        "approved_by_level": admin_level
    }


class RejectWithReasonRequest(BaseModel):
    reason: str
    return_to_user: bool = False  # اگر True باشد، به کاربر برمی‌گردد برای اصلاح


@app.post("/admin/transactions/{transaction_id}/reject")
def admin_reject_transaction(
    transaction_id: int, 
    data: RejectWithReasonRequest, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    رد تراکنش با ثبت دلیل
    
    اگر return_to_user=True باشد، تراکنش به DRAFT برمی‌گردد
    در غیر این صورت به REJECTED می‌رود (رد نهایی)
    """
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    if not current_user.role.startswith("ADMIN_L") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
    
    # وضعیت‌های قابل رد
    rejectable_statuses = ["PENDING_L1", "PENDING_L2", "PENDING_L3", "PENDING_L4", "pending"]
    if t.status not in rejectable_statuses:
        raise HTTPException(status_code=400, detail=f"تراکنش در وضعیت {t.status} قابل رد نیست")
    
    previous_status = t.status
    
    # تعیین سطح ادمین
    admin_level = current_user.admin_level or 1
    if current_user.role == "admin":
        admin_level = 4  # ادمین قدیمی = سطح ۴
    
    # آزادسازی بودجه رزرو شده
    if t.budget_item_id:
        budget = db.query(models.BudgetItem).filter(models.BudgetItem.id == t.budget_item_id).first()
        if budget:
            budget.reserved_amount = (budget.reserved_amount or 0) - (t.amount or 0)
    
    # تعیین وضعیت جدید
    if data.return_to_user:
        new_status = "DRAFT"  # برگشت به کاربر برای اصلاح
        action = "RETURN"
        message = "تراکنش به کاربر برگشت داده شد"
    else:
        new_status = "REJECTED"  # رد نهایی
        action = "REJECT"
        message = "تراکنش رد شد"
    
    # بروزرسانی تراکنش
    t.status = new_status
    t.reviewed_by_id = current_user.id
    t.reviewed_at = datetime.utcnow()
    t.rejection_reason = data.reason
    
    # ثبت در تاریخچه گردش کار
    workflow_log = models.WorkflowLog(
        transaction_id=t.id,
        admin_id=current_user.id,
        admin_level=admin_level,
        action=action,
        comment=data.reason,
        previous_status=previous_status,
        new_status=new_status
    )
    db.add(workflow_log)
    db.commit()
    
    return {
        "status": "success", 
        "message": message,
        "new_status": new_status,
        "rejected_by_level": admin_level
    }


# --- USER TRANSACTION ENDPOINTS ---

class CreateTransactionRequest(BaseModel):
    zone_id: int
    department_id: Optional[int] = None
    section_id: Optional[int] = None
    budget_code: str
    cost_center_code: Optional[str] = "000"
    continuous_activity_code: Optional[str] = "00"
    special_activity: Optional[str] = ""
    financial_event_code: Optional[str] = "000"
    beneficiary_name: str
    contract_number: Optional[str] = "0000"
    amount: float
    description: Optional[str] = ""
    form_data: Optional[dict] = None

@app.post("/portal/transactions/create")
def create_transaction(data: CreateTransactionRequest, request: Request, db: Session = Depends(get_db)):
    """Create a new transaction (user must be logged in)"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    # Get org unit codes for unique code generation
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == data.zone_id).first()
    dept = db.query(models.OrgUnit).filter(models.OrgUnit.id == data.department_id).first() if data.department_id else None
    section = db.query(models.OrgUnit).filter(models.OrgUnit.id == data.section_id).first() if data.section_id else None
    
    zone_code = (zone.code or str(data.zone_id)).zfill(2) if zone else "00"
    dept_code = (dept.code or "00").zfill(2) if dept else "00"
    section_code = (section.code or "000").zfill(3) if section else "000"
    budget_code = data.budget_code.zfill(4) if data.budget_code else "0000"
    cost_center = (data.cost_center_code or "000").zfill(3)
    cont_act = (data.continuous_activity_code or "00").zfill(2)
    spec_act_hash = hashlib.md5(data.special_activity.encode()).hexdigest()[:3].upper() if data.special_activity else "000"
    name_clean = data.beneficiary_name.strip() or "Unknown"
    ben_hash = hashlib.md5(name_clean.encode()).hexdigest()[:6].upper()
    fin_event = (data.financial_event_code or "000").zfill(3)
    date_code = "1403"  # Current fiscal year
    
    # Count existing transactions with same prefix
    existing_prefix = f"{zone_code}-{dept_code}-{section_code}-{budget_code}"
    count_query = db.query(models.Transaction).filter(
        models.Transaction.unique_code.like(f"{existing_prefix}%")
    ).count()
    occurrence = str(count_query + 1).zfill(3)
    
    unique_code = f"{zone_code}-{dept_code}-{section_code}-{budget_code}-{cost_center}-{cont_act}-{spec_act_hash}-{ben_hash}-{fin_event}-{date_code}-{occurrence}"
    
    # Get budget item ID
    budget_item = db.query(models.BudgetItem).filter(models.BudgetItem.budget_code == data.budget_code).first()
    
    # Check budget availability
    if budget_item:
        remaining = (budget_item.remaining_budget or budget_item.allocated_1403 or 0) - (budget_item.reserved_amount or 0)
        if remaining < data.amount:
            raise HTTPException(status_code=400, detail=f"بودجه کافی نیست. مانده: {remaining:,.0f} ریال")
        # Reserve budget
        budget_item.reserved_amount = (budget_item.reserved_amount or 0) + data.amount
    
    # Get related IDs
    cost_center_ref = db.query(models.CostCenterRef).filter(models.CostCenterRef.code == data.cost_center_code).first()
    cont_action = db.query(models.ContinuousAction).filter(models.ContinuousAction.code == data.continuous_activity_code).first()
    fin_event_ref = db.query(models.FinancialEventRef).filter(models.FinancialEventRef.code == data.financial_event_code).first()
    
    # Create transaction
    transaction = models.Transaction(
        unique_code=unique_code,
        status="PENDING_L1",  # شروع گردش کار از سطح ۱
        current_approval_level=0,
        created_by_id=current_user.id,
        zone_id=data.zone_id,
        department_id=data.department_id,
        section_id=data.section_id,
        budget_item_id=budget_item.id if budget_item else None,
        cost_center_id=cost_center_ref.id if cost_center_ref else None,
        continuous_action_id=cont_action.id if cont_action else None,
        financial_event_id=fin_event_ref.id if fin_event_ref else None,
        amount=data.amount,
        beneficiary_name=data.beneficiary_name,
        contract_number=data.contract_number,
        special_activity=data.special_activity,
        description=data.description,
        form_data=data.form_data,
        fiscal_year="1403"
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    return {
        "status": "success",
        "message": "تراکنش با موفقیت ایجاد شد و در انتظار تایید است",
        "transaction_id": transaction.id,
        "unique_code": unique_code,
        "parts": {
            "zone": zone_code,
            "dept": dept_code,
            "section": section_code,
            "budget": budget_code,
            "cost_center": cost_center,
            "continuous_activity": cont_act,
            "special_activity": spec_act_hash,
            "beneficiary": ben_hash,
            "financial_event": fin_event,
            "date": date_code,
            "occurrence": occurrence
        }
    }

@app.get("/portal/my-transactions")
def get_my_transactions(request: Request, db: Session = Depends(get_db)):
    """Get current user's transactions"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    transactions = db.query(models.Transaction).filter(
        models.Transaction.created_by_id == current_user.id
    ).order_by(models.Transaction.created_at.desc()).limit(50).all()
    
    result = []
    for t in transactions:
        result.append({
            "id": t.id,
            "unique_code": t.unique_code,
            "beneficiary_name": t.beneficiary_name,
            "amount": t.amount,
            "status": t.status,
            "created_at": t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None
        })
    
    return {"transactions": result, "count": len(result)}


# --- USER ALLOWED ACTIVITIES API ---

@app.get("/portal/user/allowed-activities")
def get_user_allowed_activities(request: Request, db: Session = Depends(get_db)):
    """
    دریافت فعالیت‌های مجاز کاربر بر اساس قسمت کاربر
    
    این API جایگزین انتخاب دستی سامانه می‌شود.
    بر اساس section_id کاربر، سامانه‌ها و فعالیت‌های مجاز را برمی‌گرداند.
    """
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    
    # دریافت قسمت کاربر
    section_id = current_user.default_section_id
    section = None
    if section_id:
        section = db.query(models.OrgUnit).filter(models.OrgUnit.id == section_id).first()
    
    # دریافت سامانه‌های مجاز قسمت
    if section_id:
        # بررسی جدول ارتباط قسمت-سامانه
        mappings = db.query(models.SectionSubsystemAccess).filter(
            models.SectionSubsystemAccess.section_id == section_id
        ).all()
        
        if mappings:
            subsystem_ids = [m.subsystem_id for m in mappings]
            subsystems = db.query(models.Subsystem).filter(
                models.Subsystem.id.in_(subsystem_ids),
                models.Subsystem.is_active == True
            ).order_by(models.Subsystem.order).all()
        else:
            # اگر ارتباطی تعریف نشده، همه سامانه‌ها را برگردان
            subsystems = db.query(models.Subsystem).filter(
                models.Subsystem.is_active == True
            ).order_by(models.Subsystem.order).all()
    else:
        # اگر کاربر قسمت ندارد، همه سامانه‌ها را برگردان
        subsystems = db.query(models.Subsystem).filter(
            models.Subsystem.is_active == True
        ).order_by(models.Subsystem.order).all()
    
    # ساخت پاسخ با فعالیت‌های هر سامانه
    result_subsystems = []
    for s in subsystems:
        activities = db.query(models.SubsystemActivity).filter(
            models.SubsystemActivity.subsystem_id == s.id,
            models.SubsystemActivity.is_active == True
        ).order_by(models.SubsystemActivity.order).all()
        
        result_subsystems.append({
            "id": s.id,
            "code": s.code,
            "title": s.title,
            "icon": s.icon,
            "attachment_type": s.attachment_type,
            "activities": [
                {
                    "id": a.id,
                    "code": a.code,
                    "title": a.title,
                    "form_type": a.form_type
                }
                for a in activities
            ]
        })
    
    return {
        "user": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "role": current_user.role
        },
        "user_section": {
            "id": section.id if section else None,
            "title": section.title if section else None,
            "code": section.code if section else None
        },
        "allowed_subsystems": result_subsystems,
        "subsystem_count": len(result_subsystems)
    }


# --- SUBSYSTEMS API ENDPOINTS ---

@app.get("/portal/subsystems")
def get_subsystems(db: Session = Depends(get_db)):
    """Get all active subsystems (14 سامانه)"""
    subsystems = db.query(models.Subsystem).filter(
        models.Subsystem.is_active == True
    ).order_by(models.Subsystem.order).all()
    
    return {
        "count": len(subsystems),
        "subsystems": [
            {
                "id": s.id,
                "code": s.code,
                "title": s.title,
                "icon": s.icon,
                "attachment_type": s.attachment_type,
                "order": s.order
            }
            for s in subsystems
        ]
    }


@app.get("/portal/subsystems/{subsystem_id}/activities")
def get_subsystem_activities(subsystem_id: int, db: Session = Depends(get_db)):
    """Get activities (فعالیت‌های ویژه) for a specific subsystem"""
    subsystem = db.query(models.Subsystem).filter(
        models.Subsystem.id == subsystem_id
    ).first()
    
    if not subsystem:
        raise HTTPException(status_code=404, detail="سامانه یافت نشد")
    
    activities = db.query(models.SubsystemActivity).filter(
        models.SubsystemActivity.subsystem_id == subsystem_id,
        models.SubsystemActivity.is_active == True
    ).order_by(models.SubsystemActivity.order).all()
    
    return {
        "subsystem": {
            "id": subsystem.id,
            "code": subsystem.code,
            "title": subsystem.title
        },
        "count": len(activities),
        "activities": [
            {
                "id": a.id,
                "code": a.code,
                "title": a.title,
                "form_type": a.form_type
            }
            for a in activities
        ]
    }


@app.get("/portal/subsystems/for-section/{section_id}")
def get_subsystems_for_section(section_id: int, db: Session = Depends(get_db)):
    """
    Get subsystems accessible by a specific section (قسمت).
    If no mapping exists, returns all active subsystems.
    """
    # Check if section has specific subsystem mappings
    mappings = db.query(models.SectionSubsystemAccess).filter(
        models.SectionSubsystemAccess.section_id == section_id
    ).all()
    
    if mappings:
        # Return only mapped subsystems
        subsystem_ids = [m.subsystem_id for m in mappings]
        subsystems = db.query(models.Subsystem).filter(
            models.Subsystem.id.in_(subsystem_ids),
            models.Subsystem.is_active == True
        ).order_by(models.Subsystem.order).all()
    else:
        # No specific mapping - return all active subsystems
        subsystems = db.query(models.Subsystem).filter(
            models.Subsystem.is_active == True
        ).order_by(models.Subsystem.order).all()
    
    return {
        "section_id": section_id,
        "count": len(subsystems),
        "subsystems": [
            {
                "id": s.id,
                "code": s.code,
                "title": s.title,
                "icon": s.icon,
                "attachment_type": s.attachment_type
            }
            for s in subsystems
        ]
    }


@app.get("/portal/org/roots")


def get_root_orgs(db: Session = Depends(get_db)):
    """Get top-level zones (Level 1)"""
    return db.query(models.OrgUnit).filter(models.OrgUnit.parent_id == None).all()

@app.get("/portal/org/children/{parent_id}")
def get_org_children(parent_id: int, db: Session = Depends(get_db)):
    """Get children of a specific unit"""
    return db.query(models.OrgUnit).filter(models.OrgUnit.parent_id == parent_id).all()


# --- NEW: ORG-CONTEXT FILTERED ENDPOINTS ---
# These endpoints derive data from Hesabdary Information.xlsx via OrgBudgetMap table
# No manual trustee selection required

@app.get("/portal/budgets/for-org")
def get_budgets_for_org(
    zone_id: int,
    department_id: Optional[int] = None,
    section_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get budgets for the selected org context.
    Source: OrgBudgetMap (from Hesabdary Information.xlsx) joined with BudgetItem table.
    No trustee parameter needed - it's inferred from org context.
    """
    # Get zone code from zone_id
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == zone_id).first()
    if not zone:
        return []
    
    zone_code = zone.code
    print(f"[DEBUG] Fetching budgets for org: zone_id={zone_id}, zone_code={zone_code}")
    
    # Get distinct budget codes from OrgBudgetMap for this zone
    budget_codes_query = db.query(models.OrgBudgetMap.budget_code).filter(
        models.OrgBudgetMap.zone_code == zone_code,
        models.OrgBudgetMap.budget_code != None,
        models.OrgBudgetMap.budget_code != ""
    ).distinct()
    
    budget_codes = [bc[0] for bc in budget_codes_query.all()]
    print(f"[DEBUG] Found {len(budget_codes)} distinct budget codes in OrgBudgetMap")
    
    if not budget_codes:
        return []
    
    # Get budget items that match these codes
    items = db.query(models.BudgetItem).filter(
        models.BudgetItem.budget_code.in_(budget_codes)
    ).order_by(models.BudgetItem.budget_code).limit(500).all()
    
    print(f"[DEBUG] Returning {len(items)} budget items")
    
    return [
        {
            "id": item.id,
            "budget_code": item.budget_code,
            "title": item.description,
            "description": item.description,
            "allocated_1403": item.allocated_1403 or 0,
            "remaining_budget": item.remaining_budget or 0,
            "budget_type": item.budget_type,
            "row_type": item.row_type,
            "zone_code": item.zone_code,
            "trustee": item.trustee,
        }
        for item in items
    ]


@app.get("/portal/cost-centers/for-org")
def get_cost_centers_for_org(
    zone_id: int,
    department_id: Optional[int] = None,
    section_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get cost centers for the selected org context.
    Source: OrgBudgetMap.cost_center_desc column (from Hesabdary Information.xlsx).
    """
    # Get zone code from zone_id
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == zone_id).first()
    if not zone:
        return []
    
    zone_code = zone.code
    print(f"[DEBUG] Fetching cost centers for org: zone_id={zone_id}, zone_code={zone_code}")
    
    # Get distinct cost center descriptions from OrgBudgetMap
    cost_centers_query = db.query(models.OrgBudgetMap.cost_center_desc).filter(
        models.OrgBudgetMap.zone_code == zone_code,
        models.OrgBudgetMap.cost_center_desc != None,
        models.OrgBudgetMap.cost_center_desc != ""
    ).distinct()
    
    cost_center_descs = [cc[0] for cc in cost_centers_query.all()]
    print(f"[DEBUG] Found {len(cost_center_descs)} distinct cost centers")
    
    # Return as list with auto-generated IDs
    return [
        {
            "id": idx + 1,
            "code": f"CC-{str(idx + 1).zfill(4)}",
            "title": desc,
            "name": desc,
        }
        for idx, desc in enumerate(cost_center_descs)
    ]


@app.get("/portal/continuous-actions/for-org")
def get_continuous_actions_for_org(
    zone_id: int,
    department_id: Optional[int] = None,
    section_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get continuous actions for the selected org context.
    Source: OrgBudgetMap.continuous_action_desc column (شرح سرفصل حساب جزء from Hesabdary Information.xlsx).
    """
    # Get zone code from zone_id
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == zone_id).first()
    if not zone:
        return []
    
    zone_code = zone.code
    print(f"[DEBUG] Fetching continuous actions for org: zone_id={zone_id}, zone_code={zone_code}")
    
    # Get distinct continuous action descriptions from OrgBudgetMap
    actions_query = db.query(models.OrgBudgetMap.continuous_action_desc).filter(
        models.OrgBudgetMap.zone_code == zone_code,
        models.OrgBudgetMap.continuous_action_desc != None,
        models.OrgBudgetMap.continuous_action_desc != ""
    ).distinct().limit(200)
    
    action_descs = [a[0] for a in actions_query.all()]
    print(f"[DEBUG] Found {len(action_descs)} distinct continuous actions")
    
    # Return as list with auto-generated IDs
    return [
        {
            "id": idx + 1,
            "code": f"CA-{str(idx + 1).zfill(3)}",
            "title": desc,
            "name": desc,
        }
        for idx, desc in enumerate(action_descs)
    ]


@app.get("/portal/budgets/trustees/{zone_code}")
def get_trustees_for_zone(zone_code: str, db: Session = Depends(get_db)):
    """Get distinct trustees for budget items in a zone"""
    
    # Find the zone by code
    selected_zone = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == zone_code,
        models.OrgUnit.parent_id == None  # Root level
    ).first()
    
    if not selected_zone:
        return {"trustees": []}
    
    # Get all org unit IDs in selected zone's hierarchy
    zone_ids = [selected_zone.id]
    children = db.query(models.OrgUnit.id).filter(
        models.OrgUnit.parent_id == selected_zone.id
    ).all()
    zone_ids.extend([c[0] for c in children])
    
    for child_id in [c[0] for c in children]:
        grandchildren = db.query(models.OrgUnit.id).filter(
            models.OrgUnit.parent_id == child_id
        ).all()
        zone_ids.extend([g[0] for g in grandchildren])
    
    # Get distinct trustees for budgets in this zone
    trustees = db.query(models.BudgetItem.trustee).filter(
        models.BudgetItem.trustee_section_id.in_(zone_ids),
        models.BudgetItem.trustee != None,
        models.BudgetItem.trustee != ""
    ).distinct().all()
    
    return {
        "zone_code": zone_code,
        "zone_title": selected_zone.title,
        "trustees": [t[0] for t in trustees if t[0]]
    }


@app.get("/portal/budgets/by-zone/{zone_code}")
def get_budgets_by_zone_code(zone_code: str, trustee: str = "", request: Request = None, db: Session = Depends(get_db)):
    """Get budgets filtered by SELECTED zone and optionally by trustee"""
    
    query = db.query(models.BudgetItem)
    
    # Find the zone by code to get its ID and children
    selected_zone = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == zone_code,
        models.OrgUnit.parent_id == None  # Root level
    ).first()
    
    if selected_zone:
        print(f"[DEBUG] Selected zone: {selected_zone.id} - {selected_zone.title}")
        
        # Get all org unit IDs in selected zone's hierarchy
        zone_ids = [selected_zone.id]
        
        # Get children
        children = db.query(models.OrgUnit.id).filter(
            models.OrgUnit.parent_id == selected_zone.id
        ).all()
        zone_ids.extend([c[0] for c in children])
        
        # Get grandchildren
        for child_id in [c[0] for c in children]:
            grandchildren = db.query(models.OrgUnit.id).filter(
                models.OrgUnit.parent_id == child_id
            ).all()
            zone_ids.extend([g[0] for g in grandchildren])
        
        print(f"[DEBUG] Zone hierarchy has {len(zone_ids)} org units")
        
        # Filter budgets by trustee_section_id matching zone hierarchy
        query = query.filter(
            models.BudgetItem.trustee_section_id.in_(zone_ids)
        )
    else:
        print(f"[DEBUG] Zone code '{zone_code}' not found, showing all budgets")
    
    # Filter by trustee if provided
    if trustee:
        query = query.filter(models.BudgetItem.trustee == trustee)
        print(f"[DEBUG] Filtering by trustee: {trustee}")
    
    items = query.order_by(models.BudgetItem.budget_code).limit(500).all()
    print(f"[DEBUG] Returning {len(items)} budget items")

    return [
        {
            "id": item.id,
            "budget_code": item.budget_code,
            "title": item.description,
            "description": item.description,
            "allocated_1403": item.allocated_1403 or 0,
            "remaining_budget": item.remaining_budget or 0,
            "budget_type": item.budget_type,
            "row_type": item.row_type,
            "zone_code": item.zone_code,
            "trustee": item.trustee,
            "trustee_section_id": item.trustee_section_id
        }
        for item in items
    ]

@app.get("/portal/budgets/all")
def get_all_budgets(limit: int = 100, search: str = "", db: Session = Depends(get_db)):
    """Get all budget items with optional search"""
    query = db.query(models.BudgetItem)
    if search:
        query = query.filter(
            or_(
                models.BudgetItem.budget_code.contains(search),
                models.BudgetItem.description.contains(search)
            )
        )
    items = query.order_by(models.BudgetItem.budget_code).limit(limit).all()
    return [
        {
            "id": item.id,
            "budget_code": item.budget_code,
            "title": item.description,
            "allocated_1403": item.allocated_1403 or 0,
            "remaining_budget": item.remaining_budget or 0,
            "budget_type": item.budget_type
        }
        for item in items
    ]


# --- SUBMIT ACTION (11-PART UNIQUE CODE) ---

class PortalSubmit(BaseModel):
    zone: str
    dept_code: str = "00"
    section_code: str = "000"
    budget_code: str
    budget_title: str = ""
    cost_center: str = "000"
    continuous_activity: str = "00"
    special_activity: str = ""
    contractor_name: str
    contract_number: str = "0000"
    financial_event: str = "000"
    date: str

@app.post("/portal/submit")
def submit_action(data: PortalSubmit, db: Session = Depends(get_db)):
    """Generate 11-Part Unique Code"""
    zone_code = data.zone.zfill(2) if data.zone.isdigit() else "00"
    dept_code = data.dept_code.zfill(2) if data.dept_code else "00"
    section_code = data.section_code.zfill(3) if data.section_code else "000"
    budget_code = data.budget_code.zfill(4) if data.budget_code else "0000"
    cost_center = data.cost_center.zfill(3) if data.cost_center else "000"
    cont_act = data.continuous_activity.zfill(2) if data.continuous_activity else "00"
    spec_act_hash = hashlib.md5(data.special_activity.encode()).hexdigest()[:3].upper() if data.special_activity else "000"
    name_clean = data.contractor_name.strip() or "Unknown"
    ben_hash = hashlib.md5(name_clean.encode()).hexdigest()[:6].upper()
    fin_event = data.financial_event.zfill(3) if data.financial_event else "000"
    date_code = data.date.split("/")[0] if "/" in data.date else data.date[:4]
    
    existing_prefix = f"{zone_code}-{dept_code}-{section_code}-{budget_code}"
    count_query = db.query(models.SpecialAction).filter(
        models.SpecialAction.unique_code.like(f"{existing_prefix}%")
    ).count()
    occurrence = str(count_query + 1).zfill(3)
    
    unique_code = f"{zone_code}-{dept_code}-{section_code}-{budget_code}-{cost_center}-{cont_act}-{spec_act_hash}-{ben_hash}-{fin_event}-{date_code}-{occurrence}"
    
    return {
        "status": "success",
        "generated_code": unique_code,
        "message": "کد یکتا 11 قسمتی با موفقیت تولید شد",
        "parts": {
            "zone": zone_code,
            "dept": dept_code,
            "section": section_code,
            "budget": budget_code,
            "cost_center": cost_center,
            "continuous_activity": cont_act,
            "special_activity": spec_act_hash,
            "beneficiary": ben_hash,
            "financial_event": fin_event,
            "date": date_code,
            "occurrence": occurrence
        }
    }

# --- SERVE HTML ---
@app.get("/login", response_class=HTMLResponse)
def read_login():
    """Serve login page"""
    try:
        with open("login.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: login.html not found!</h1>"

@app.get("/portal", response_class=HTMLResponse)
def read_portal():
    """Serve React app (Figma-based UI) for portal"""
    react_index = os.path.join(REACT_BUILD_PATH, "index.html")
    if os.path.exists(react_index):
        with open(react_index, "r", encoding="utf-8") as f:
            html = f.read()
            # Update asset paths to use /react-assets
            html = html.replace('="/assets/', '="/react-assets/')
            html = html.replace("='/assets/", "='/react-assets/")
            return html
    # Fallback to old portal.html if React build not found
    try:
        with open("portal.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: portal not found!</h1>"


@app.get("/admin", response_class=HTMLResponse)
def read_admin():
    """Serve admin dashboard"""
    try:
        with open("admin.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: admin.html not found!</h1>"

@app.get("/portal/test2", response_class=HTMLResponse)
def read_test_mode2():
    """Serve Test Mode 2 page - Budget-based verification"""
    try:
        with open("test_mode2.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: test_mode2.html not found!</h1>"

@app.get("/")
def root():
    return RedirectResponse(url="/login")



@app.get("/portal/continuous-actions")
def get_continuous_actions(search: str = "", db: Session = Depends(get_db)):
    query = db.query(models.ContinuousAction)
    if search:
        query = query.filter(models.ContinuousAction.title.contains(search))
    return query.limit(100).all()

@app.get("/portal/financial-events")
def get_financial_events(db: Session = Depends(get_db)):
    return db.query(models.FinancialEventRef).order_by(models.FinancialEventRef.code).all()

@app.get("/portal/cost-centers")
def get_cost_centers(db: Session = Depends(get_db)):
    return db.query(models.CostCenterRef).all()

@app.get("/portal/reports/financial-docs/{zone_code}")
def get_financial_docs(zone_code: str, db: Session = Depends(get_db)):
    """Get financial documents for a specific zone"""
    return db.query(models.FinancialDocument).filter(models.FinancialDocument.zone_code == zone_code).limit(100).all()


# --- TEST MODE: Event-based Excel Reading ---

@app.get("/portal/test/sheets")
def get_excel_sheets():
    """Get list of sheets (financial event types) from Excel"""
    try:
        sheet_names = get_sheet_names()
        sheets = []
        for name in sheet_names:
            # Clean display name (remove extra spaces)
            display_name = name.strip()
            sheets.append({
                "name": name,  # Keep original name for API calls
                "display_name": display_name,
                "row_count": 0,  # Will be loaded on demand
                "request_count": 0
            })
        return {"sheets": sheets}
    except Exception as e:
        return {"error": str(e), "sheets": []}


@app.get("/portal/test/requests/{sheet_name:path}")
def get_sheet_requests(sheet_name: str):
    """Get list of request numbers for a specific sheet (Zone 20 only)"""
    try:
        # Try to find matching sheet name (handle encoding issues)
        actual_sheet_name = None
        for name in get_sheet_names():
            if name == sheet_name or name.strip() == sheet_name.strip():
                actual_sheet_name = name
                break
        
        if actual_sheet_name is None:
            return {"error": f"Sheet not found: {sheet_name}", "requests": []}
        
        df = pd.read_excel(EXCEL_FILE, sheet_name=actual_sheet_name)
        df20 = df[df['AreaNo'] == ZONE_FILTER]
        
        if len(df20) == 0:
            return {
                "sheet_name": actual_sheet_name,
                "zone": ZONE_FILTER,
                "message": "این شیت داده‌ای برای منطقه ۲۰ ندارد",
                "requests": []
            }
        
        # Clean request values and group
        request_stats = {}
        for idx, row in df20.iterrows():
            raw_req = row.get('Requests')
            clean_req = clean_request_id(raw_req)
            if clean_req is None:
                continue
            
            if clean_req not in request_stats:
                request_stats[clean_req] = {
                    "raw_value": raw_req,  # Keep original for filtering
                    "count": 0,
                    "total_debit": 0.0,
                    "total_credit": 0.0
                }
            
            request_stats[clean_req]["count"] += 1
            debit = row.get('DebitAmnt', 0)
            credit = row.get('CreditAmnt', 0)
            request_stats[clean_req]["total_debit"] += float(debit) if pd.notna(debit) else 0.0
            request_stats[clean_req]["total_credit"] += float(credit) if pd.notna(credit) else 0.0
        
        requests = []
        for clean_req, stats in request_stats.items():
            total_debit = stats["total_debit"]
            total_credit = stats["total_credit"]
            requests.append({
                "request_id": clean_req,  # Clean display value
                "request_raw": str(stats["raw_value"]),  # Original value for filtering
                "transaction_count": int(stats["count"]),
                "total_debit": float(total_debit),
                "total_credit": float(total_credit),
                "is_balanced": bool(abs(total_debit - total_credit) < 1)
            })
        
        # Sort by transaction count descending
        requests.sort(key=lambda x: x['transaction_count'], reverse=True)
        
        return {
            "sheet_name": actual_sheet_name,
            "zone": int(ZONE_FILTER),
            "requests": requests
        }
    except Exception as e:
        return {"error": str(e), "requests": []}


@app.get("/portal/test/transactions/{sheet_name:path}/{request_id}")
def get_request_transactions(sheet_name: str, request_id: str):
    """Get all transactions for a specific request"""
    try:
        # Find matching sheet name
        actual_sheet_name = None
        for name in get_sheet_names():
            if name == sheet_name or name.strip() == sheet_name.strip():
                actual_sheet_name = name
                break
        
        if actual_sheet_name is None:
            return {"error": f"Sheet not found: {sheet_name}", "transactions": []}
        
        df = pd.read_excel(EXCEL_FILE, sheet_name=actual_sheet_name)
        df20 = df[df['AreaNo'] == ZONE_FILTER]
        
        # Filter by cleaned request ID
        transactions = []
        for idx, row in df20.iterrows():
            raw_req = row.get('Requests')
            clean_req = clean_request_id(raw_req)
            
            # Match by clean value or raw value
            if clean_req == request_id or str(raw_req).strip() == request_id:
                transactions.append({
                    "row_id": int(idx),
                    "doc_no": safe_str(row.get("DocNo"), ""),
                    "titk_no": safe_str(row.get("TitkNo"), ""),
                    "titk_name": safe_str(row.get("TitkNam"), ""),
                    "titm_no": safe_str(row.get("TitMNo"), ""),
                    "titm_name": safe_str(row.get("TitMNam"), ""),
                    "titt_no": safe_str(row.get("TitTNo"), ""),
                    "titt_name": safe_str(row.get("TitTNam"), ""),
                    "titj_no": safe_str(row.get("TitJNo"), ""),
                    "titj_name": safe_str(row.get("TitJNam"), ""),
                    "radk_no": safe_str(row.get("RadKNo"), ""),
                    "radm_no": safe_str(row.get("RadMNo"), ""),
                    "radt_no": safe_str(row.get("RadTNo"), ""),
                    "radj_no": safe_str(row.get("RadJNo"), ""),
                    "radj_name": safe_str(row.get("RadJNam"), ""),
                    "opr_cod": safe_str(row.get("OprCod"), ""),
                    "debit": float(row.get("DebitAmnt", 0)) if pd.notna(row.get("DebitAmnt")) else 0,
                    "credit": float(row.get("CreditAmnt", 0)) if pd.notna(row.get("CreditAmnt")) else 0,
                    "budget_no": safe_str(row.get("BodgetNo"), ""),
                    "type_desc": safe_str(row.get("TypDesc"), "")
                })
        
        total_debit = sum(t['debit'] for t in transactions)
        total_credit = sum(t['credit'] for t in transactions)
        
        return {
            "sheet_name": actual_sheet_name,
            "request_id": request_id,
            "zone": int(ZONE_FILTER),
            "transaction_count": int(len(transactions)),
            "total_debit": float(total_debit),
            "total_credit": float(total_credit),
            "balance": float(total_debit - total_credit),
            "is_balanced": bool(abs(total_debit - total_credit) < 1),
            "transactions": transactions
        }
    except Exception as e:
        return {"error": str(e), "transactions": []}


# --- TEST MODE 2: Budget-based with Transaction Integration ---
# Uses: اعتبارات هزینه‌ای + تملک دارایی سرمایه‌ای (budget reference)
# And: _شهرداری مرکزی گزارش دفتر مرکزی1403.xlsx (transactions)

TRANSACTION_FILE = "_شهرداری مرکزی گزارش دفتر مرکزی1403.xlsx"
_transaction_df_cache = None

def get_transaction_df():
    """Load and cache transaction dataframe with preprocessed BodgetNo"""
    global _transaction_df_cache
    if _transaction_df_cache is None:
        df = pd.read_excel(TRANSACTION_FILE)
        # Convert BodgetNo to clean string (handle float like 11010201.0 -> "11010201")
        df['BodgetNo_str'] = df['BodgetNo'].apply(
            lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (int, float)) else str(x).strip() if pd.notna(x) else ""
        )
        _transaction_df_cache = df
    return _transaction_df_cache



@app.get("/portal/test2/budget-items")
def get_budget_items(
    search: str = "",
    trustee: str = "",
    subject: str = "",
    row_type: str = "",
    budget_type: str = "",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get budget items with filters"""
    query = db.query(models.BudgetItem)
    
    if search:
        query = query.filter(
            or_(
                models.BudgetItem.budget_code.contains(search),
                models.BudgetItem.description.contains(search)
            )
        )
    if trustee:
        query = query.filter(models.BudgetItem.trustee.contains(trustee))
    if subject:
        query = query.filter(models.BudgetItem.subject.contains(subject))
    if row_type:
        query = query.filter(models.BudgetItem.row_type == row_type)
    if budget_type:
        query = query.filter(models.BudgetItem.budget_type == budget_type)
    
    items = query.limit(limit).all()
    
    return {
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "budget_code": item.budget_code,
                "description": item.description,
                "budget_type": item.budget_type,
                "zone": item.zone,
                "trustee": item.trustee,
                "subject": item.subject,
                "sub_subject": item.sub_subject,
                "row_type": item.row_type,
                "approved_1403": item.approved_1403,
                "allocated_1403": item.allocated_1403,
                "spent_1403": item.spent_1403
            }
            for item in items
        ]
    }


@app.get("/portal/test2/budget-items/{budget_code}")
def get_budget_item_detail(budget_code: str, db: Session = Depends(get_db)):
    """Get single budget item with transaction summary"""
    item = db.query(models.BudgetItem).filter(
        models.BudgetItem.budget_code == budget_code
    ).first()
    
    if not item:
        return {"error": f"Budget code not found: {budget_code}"}
    
    # Get transaction summary
    df = get_transaction_df()
    df_filtered = df[df['BodgetNo_str'] == budget_code]
    
    total_debit = df_filtered['DebitAmnt'].sum() if len(df_filtered) > 0 else 0
    total_credit = df_filtered['CreditAmnt'].sum() if len(df_filtered) > 0 else 0
    
    return {
        "budget_item": {
            "budget_code": item.budget_code,
            "description": item.description,
            "budget_type": item.budget_type,
            "zone": item.zone,
            "trustee": item.trustee,
            "subject": item.subject,
            "sub_subject": item.sub_subject,
            "row_type": item.row_type,
            "approved_1403": item.approved_1403,
            "allocated_1403": item.allocated_1403,
            "spent_1403": item.spent_1403
        },
        "transaction_summary": {
            "count": int(len(df_filtered)),
            "total_debit": float(total_debit) if pd.notna(total_debit) else 0,
            "total_credit": float(total_credit) if pd.notna(total_credit) else 0,
            "balance": float(total_debit - total_credit) if pd.notna(total_debit) and pd.notna(total_credit) else 0,
            "has_transactions": len(df_filtered) > 0
        }
    }


@app.get("/portal/test2/events/{budget_code}")
def get_events_for_budget(budget_code: str):
    """Get financial event types (TypDesc) for a budget code"""
    df = get_transaction_df()
    df_filtered = df[df['BodgetNo_str'] == budget_code]
    
    if len(df_filtered) == 0:
        return {"budget_code": budget_code, "events": [], "message": "تراکنشی برای این کد بودجه یافت نشد"}
    
    # Group by event type
    events = []
    for event_type in df_filtered['TypDesc'].dropna().unique():
        df_event = df_filtered[df_filtered['TypDesc'] == event_type]
        events.append({
            "event_type": str(event_type),
            "transaction_count": int(len(df_event)),
            "total_debit": float(df_event['DebitAmnt'].sum()),
            "total_credit": float(df_event['CreditAmnt'].sum())
        })
    
    # Sort by transaction count
    events.sort(key=lambda x: x['transaction_count'], reverse=True)
    
    return {"budget_code": budget_code, "events": events}


@app.get("/portal/test2/requests/{budget_code}/{event_type}")
def get_requests_for_event(budget_code: str, event_type: str):
    """Get request codes for a budget code and event type"""
    df = get_transaction_df()
    
    # First, find the relevant request IDs associated with this budget code and event
    # We still filter by budget_code first to find WHICH requests to show
    initial_filter = df[
        (df['BodgetNo_str'] == budget_code) &
        (df['TypDesc'].astype(str) == event_type)
    ]
    
    if len(initial_filter) == 0:
        return {"budget_code": budget_code, "event_type": event_type, "requests": []}
    
    # Group by request
    requests = []
    # Get unique request IDs associated with this budget code
    unique_request_ids = initial_filter['Requests'].dropna().unique()
    
    for request_id in unique_request_ids:
        # CRITICAL FIX: For the totals and balance, we look at the ENTIRE dataframe
        # for this request_id, NOT restricted by budget_code.
        # This includes rows that might have NaN budget codes but are part of the same request.
        # Ensure strict type matching for request_id filtering
        df_req_all = df[df['Requests'] == request_id]
        
        total_debit = df_req_all['DebitAmnt'].sum()
        total_credit = df_req_all['CreditAmnt'].sum()
        
        requests.append({
            "request_id": str(request_id).strip(),
            "transaction_count": int(len(df_req_all)),
            "total_debit": float(total_debit),
            "total_credit": float(total_credit),
            "is_balanced": bool(abs(total_debit - total_credit) < 1)
        })
    
    # Sort by transaction count
    requests.sort(key=lambda x: x['transaction_count'], reverse=True)
    
    return {"budget_code": budget_code, "event_type": event_type, "requests": requests}


@app.get("/portal/test2/transactions/{budget_code}/{event_type}/{request_id}")
def get_transactions_detail(budget_code: str, event_type: str, request_id: str):
    """Get detailed transactions for budget code, event, and request"""
    df = get_transaction_df()
    
    # CRITICAL FIX: To show the full balanced document, we fetch ALL rows for this request_id
    # regardless of budget_code or event_type (since a single request might span types or lack codes)
    # We use the request_id passed from the previous step.
    
    # Convert request_id from URL (str) to the type in dataframe (likely int or float, but stored as object often)
    # The safest way given mixed types is comparing strings
    df_filtered = df[df['Requests'].astype(str).str.strip() == request_id]
    
    transactions = []
    for idx, row in df_filtered.iterrows():
        transactions.append({
            # Document info
            "doc_no": safe_str(row.get('DocNo')),
            "fin_year": safe_str(row.get('FinYear')),
            # Area info
            "area_no": safe_str(row.get('AreaNo')),
            "area_name": safe_str(row.get('AreaNam')),
            # Title hierarchy (سرفصل)
            "tit_k_no": safe_str(row.get('TitkNo')),
            "tit_k_name": safe_str(row.get('TitkNam')),
            "tit_m_no": safe_str(row.get('TitMNo')),
            "tit_m_name": safe_str(row.get('TitMNam')),
            "tit_t_no": safe_str(row.get('TitTNo')),
            "tit_t_name": safe_str(row.get('TitTNam')),
            "tit_j_no": safe_str(row.get('TitJNo')),
            "tit_j_name": safe_str(row.get('TitJNam')),
            # Rad hierarchy (ردیف)
            "rad_k_no": safe_str(row.get('RadKNo')),
            "rad_m_no": safe_str(row.get('RadMNo')),
            "rad_t_no": safe_str(row.get('RadTNo')),
            "rad_j_no": safe_str(row.get('RadJNo')),
            "rad_j_name": safe_str(row.get('RadJNam')),
            # Operation
            "opr_code": safe_str(row.get('OprCod')),
            # Amounts
            "debit": float(row.get('DebitAmnt', 0)) if pd.notna(row.get('DebitAmnt')) else 0,
            "credit": float(row.get('CreditAmnt', 0)) if pd.notna(row.get('CreditAmnt')) else 0,
            # Budget & Request
            "budget_no": safe_str(row.get('BodgetNo')),
            "request_id": safe_str(row.get('Requests')),
            "event_type": safe_str(row.get('TypDesc'))
        })
    
    total_debit = sum(t['debit'] for t in transactions)
    total_credit = sum(t['credit'] for t in transactions)
    
    return {
        "budget_code": budget_code,
        "event_type": event_type,
        "request_id": request_id,
        "transaction_count": len(transactions),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balance": total_debit - total_credit,
        "is_balanced": abs(total_debit - total_credit) < 1,
        "transactions": transactions
    }


@app.get("/portal/test2/filters")
def get_filter_options(db: Session = Depends(get_db)):
    """Get unique filter options for dropdowns"""
    trustees = db.query(models.BudgetItem.trustee).distinct().filter(
        models.BudgetItem.trustee != None
    ).all()
    subjects = db.query(models.BudgetItem.subject).distinct().filter(
        models.BudgetItem.subject != None
    ).all()
    
    return {
        "trustees": [t[0] for t in trustees if t[0]],
        "subjects": [s[0] for s in subjects if s[0]],
        "row_types": ["مستمر", "غیر مستمر"],
        "budget_types": ["hazine", "sarmaye"]
    }


# --- ACCOUNT CODES (CODYEKTA) API ---

@app.get("/api/account-codes")
def get_account_codes(
    category: str = "",
    search: str = "",
    zone_code: str = "",
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all account codes with filters"""
    query = db.query(models.AccountCode)
    
    if zone_code:
        query = query.filter(models.AccountCode.zone_code == zone_code)
    if category:
        query = query.filter(models.AccountCode.category == category)
    if search:
        query = query.filter(
            or_(
                models.AccountCode.unique_code.contains(search),
                models.AccountCode.budget_code.contains(search),
                models.AccountCode.request_id.contains(search)
            )
        )
    
    total = query.count()
    offset = (page - 1) * limit
    codes = query.order_by(models.AccountCode.id).offset(offset).limit(limit).all()
    
    return {
        "account_codes": [
            {
                "id": c.id,
                "unique_code": c.unique_code,
                "zone_code": c.zone_code,
                "category": c.category,
                "budget_code": c.budget_code,
                "permanent_code": c.permanent_code,
                "request_id": c.request_id,
                "transaction_type": c.transaction_type,
                "total_amount": c.total_amount,
                "temp_account_count": c.temp_account_count,
                "perm_account_count": c.perm_account_count,
                "bank_account_count": c.bank_account_count,
                "is_balanced": c.is_balanced,
                "created_at": c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else None
            }
            for c in codes
        ],
        "total": total,
        "page": page,
        "limit": limit
    }


@app.get("/api/account-codes/stats")
def get_account_codes_stats(db: Session = Depends(get_db)):
    """Get account codes statistics"""
    from sqlalchemy import func
    
    total = db.query(models.AccountCode).count()
    balanced = db.query(models.AccountCode).filter(models.AccountCode.is_balanced == True).count()
    
    # Category distribution
    category_stats = db.query(
        models.AccountCode.category,
        func.count(models.AccountCode.id),
        func.sum(models.AccountCode.total_amount)
    ).group_by(models.AccountCode.category).all()
    
    categories = {}
    for cat, count, amount in category_stats:
        categories[cat] = {
            "count": count,
            "total_amount": float(amount) if amount else 0
        }
    
    # Category labels
    category_labels = {
        "EXP": "هزینه جاری",
        "CAP": "سرمایه‌ای",
        "CON": "پیمانکاران",
        "SAL": "حقوق",
        "REV": "تنخواه",
        "WDR": "برداشت",
        "REC": "دریافت",
        "ADJ": "اصلاحی",
        "OTH": "سایر"
    }
    
    return {
        "total_codes": total,
        "balanced_codes": balanced,
        "unbalanced_codes": total - balanced,
        "categories": categories,
        "category_labels": category_labels
    }


@app.get("/api/account-codes/{code_id}")
def get_account_code_detail(code_id: int, db: Session = Depends(get_db)):
    """Get single account code detail"""
    code = db.query(models.AccountCode).filter(models.AccountCode.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="کد یافت نشد")
    
    return {
        "id": code.id,
        "unique_code": code.unique_code,
        "zone_code": code.zone_code,
        "category": code.category,
        "budget_code": code.budget_code,
        "permanent_code": code.permanent_code,
        "sequence": code.sequence,
        "request_id": code.request_id,
        "transaction_type": code.transaction_type,
        "total_amount": code.total_amount,
        "temp_account_count": code.temp_account_count,
        "perm_account_count": code.perm_account_count,
        "bank_account_count": code.bank_account_count,
        "is_balanced": code.is_balanced,
        "details": code.details,
        "created_at": code.created_at.strftime("%Y/%m/%d %H:%M") if code.created_at else None
    }


@app.get("/api/account-codes/by-request/{request_id}")
def get_account_code_by_request(request_id: str, db: Session = Depends(get_db)):
    """Get account code by request ID"""
    code = db.query(models.AccountCode).filter(
        models.AccountCode.request_id == request_id
    ).first()
    
    if not code:
        return {"found": False, "message": "کد یکتا برای این درخواست یافت نشد"}
    
    return {
        "found": True,
        "unique_code": code.unique_code,
        "category": code.category,
        "budget_code": code.budget_code,
        "total_amount": code.total_amount
    }
