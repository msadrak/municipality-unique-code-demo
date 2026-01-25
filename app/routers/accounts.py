"""
Accounts Router - Account codes API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app import models
from app.routers.auth import get_db

router = APIRouter(prefix="/api", tags=["Account Codes"])

@router.get("/account-codes")
def get_account_codes(category: str = "", search: str = "", zone_code: str = "", page: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    """Get all account codes with filters"""
    query = db.query(models.AccountCode)
    if zone_code:
        query = query.filter(models.AccountCode.zone_code == zone_code)
    if category:
        query = query.filter(models.AccountCode.category == category)
    if search:
        query = query.filter(or_(models.AccountCode.unique_code.contains(search), models.AccountCode.budget_code.contains(search), models.AccountCode.request_id.contains(search)))
    
    total = query.count()
    offset = (page - 1) * limit
    codes = query.order_by(models.AccountCode.id).offset(offset).limit(limit).all()
    
    return {"account_codes": [{"id": c.id, "unique_code": c.unique_code, "zone_code": c.zone_code, "category": c.category, "budget_code": c.budget_code, "permanent_code": c.permanent_code, "request_id": c.request_id, "transaction_type": c.transaction_type, "total_amount": c.total_amount, "is_balanced": c.is_balanced, "created_at": c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else None} for c in codes], "total": total, "page": page, "limit": limit}

@router.get("/account-codes/stats")
def get_account_codes_stats(db: Session = Depends(get_db)):
    """Get account codes statistics"""
    total = db.query(models.AccountCode).count()
    balanced = db.query(models.AccountCode).filter(models.AccountCode.is_balanced == True).count()
    
    category_stats = db.query(models.AccountCode.category, func.count(models.AccountCode.id), func.sum(models.AccountCode.total_amount)).group_by(models.AccountCode.category).all()
    categories = {cat: {"count": count, "total_amount": float(amount) if amount else 0} for cat, count, amount in category_stats}
    
    category_labels = {"EXP": "هزینه جاری", "CAP": "سرمایه‌ای", "CON": "پیمانکاران", "SAL": "حقوق", "REV": "تنخواه", "WDR": "برداشت", "REC": "دریافت", "ADJ": "اصلاحی", "OTH": "سایر"}
    return {"total_codes": total, "balanced_codes": balanced, "unbalanced_codes": total - balanced, "categories": categories, "category_labels": category_labels}

@router.get("/account-codes/{code_id}")
def get_account_code_detail(code_id: int, db: Session = Depends(get_db)):
    """Get single account code detail"""
    code = db.query(models.AccountCode).filter(models.AccountCode.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="کد یافت نشد")
    return {"id": code.id, "unique_code": code.unique_code, "zone_code": code.zone_code, "category": code.category, "budget_code": code.budget_code, "permanent_code": code.permanent_code, "sequence": code.sequence, "request_id": code.request_id, "transaction_type": code.transaction_type, "total_amount": code.total_amount, "is_balanced": code.is_balanced, "details": code.details, "created_at": code.created_at.strftime("%Y/%m/%d %H:%M") if code.created_at else None}

@router.get("/account-codes/by-request/{request_id}")
def get_account_code_by_request(request_id: str, db: Session = Depends(get_db)):
    """Get account code by request ID"""
    code = db.query(models.AccountCode).filter(models.AccountCode.request_id == request_id).first()
    if not code:
        return {"found": False, "message": "کد یکتا برای این درخواست یافت نشد"}
    return {"found": True, "unique_code": code.unique_code, "category": code.category, "budget_code": code.budget_code, "total_amount": code.total_amount}
