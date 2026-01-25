"""
Admin Router - Transaction management with 4-level workflow
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from datetime import datetime
from app import models
from app.routers.auth import get_current_user, get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

class RejectWithReasonRequest(BaseModel):
    reason: str
    return_to_user: bool = False

@router.get("/transactions")
def admin_get_transactions(request: Request, status: str = "", search: str = "", page: int = 1, limit: int = 10, my_level_only: bool = True, db: Session = Depends(get_db)):
    """Get transactions with hierarchy filtering"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    if current_user.role != "admin" and not current_user.admin_level:
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    admin_level = current_user.admin_level or 0
    query = db.query(models.Transaction)
    
    if my_level_only and 0 < admin_level < 5:
        query = query.filter(models.Transaction.status == f"PENDING_L{admin_level}")
    if status:
        query = query.filter(models.Transaction.status == status)
    if search:
        query = query.filter(or_(models.Transaction.unique_code.contains(search), models.Transaction.beneficiary_name.contains(search)))
    
    total = query.count()
    stats = {
        "total": db.query(models.Transaction).count(),
        "pending_l1": db.query(models.Transaction).filter(models.Transaction.status == "PENDING_L1").count(),
        "pending_l2": db.query(models.Transaction).filter(models.Transaction.status == "PENDING_L2").count(),
        "pending_l3": db.query(models.Transaction).filter(models.Transaction.status == "PENDING_L3").count(),
        "pending_l4": db.query(models.Transaction).filter(models.Transaction.status == "PENDING_L4").count(),
        "approved": db.query(models.Transaction).filter(models.Transaction.status == "APPROVED").count(),
        "rejected": db.query(models.Transaction).filter(models.Transaction.status == "REJECTED").count(),
    }
    
    offset = (page - 1) * limit
    transactions = query.order_by(models.Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for t in transactions:
        zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.zone_id).first() if t.zone_id else None
        result.append({"id": t.id, "unique_code": t.unique_code, "beneficiary_name": t.beneficiary_name, "amount": t.amount, "status": t.status, "zone_title": zone.title if zone else "-", "created_at": t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None})
    
    return {"transactions": result, "total": total, "page": page, "limit": limit, "stats": stats, "admin_level": admin_level}

@router.get("/transactions/{transaction_id}")
def admin_get_transaction_detail(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    """Get single transaction detail"""
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
    
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.zone_id).first() if t.zone_id else None
    dept = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.department_id).first() if t.department_id else None
    section = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.section_id).first() if t.section_id else None
    budget = db.query(models.BudgetItem).filter(models.BudgetItem.id == t.budget_item_id).first() if t.budget_item_id else None
    event = db.query(models.FinancialEventRef).filter(models.FinancialEventRef.id == t.financial_event_id).first() if t.financial_event_id else None
    created_by = db.query(models.User).filter(models.User.id == t.created_by_id).first() if t.created_by_id else None
    reviewed_by = db.query(models.User).filter(models.User.id == t.reviewed_by_id).first() if t.reviewed_by_id else None
    
    return {"id": t.id, "unique_code": t.unique_code, "status": t.status, "beneficiary_name": t.beneficiary_name, "amount": t.amount, "contract_number": t.contract_number, "special_activity": t.special_activity, "description": t.description, "zone_title": zone.title if zone else "-", "dept_title": dept.title if dept else "-", "section_title": section.title if section else "-", "budget_code": budget.budget_code if budget else "-", "budget_description": budget.description if budget else "-", "financial_event_title": event.title if event else "-", "created_by_name": created_by.full_name if created_by else "-", "reviewed_by_name": reviewed_by.full_name if reviewed_by else None, "rejection_reason": t.rejection_reason, "created_at": t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None, "reviewed_at": t.reviewed_at.strftime("%Y/%m/%d %H:%M") if t.reviewed_at else None}

@router.post("/transactions/{transaction_id}/approve")
def admin_approve_transaction(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    """Approve transaction with 4-level workflow"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    if not current_user.role.startswith("ADMIN_L") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
    
    workflow_map = {"PENDING_L1": ("PENDING_L2", "ADMIN_L1", 1), "PENDING_L2": ("PENDING_L3", "ADMIN_L2", 2), "PENDING_L3": ("PENDING_L4", "ADMIN_L3", 3), "PENDING_L4": ("APPROVED", "ADMIN_L4", 4), "pending": ("APPROVED", "admin", 1)}
    
    if t.status not in workflow_map:
        raise HTTPException(status_code=400, detail=f"تراکنش در وضعیت {t.status} قابل تایید نیست")
    
    new_status, required_role, admin_level = workflow_map[t.status]
    if current_user.role != "admin" and current_user.role != required_role:
        raise HTTPException(status_code=403, detail=f"شما سطح {current_user.role} هستید ولی این تراکنش نیاز به {required_role} دارد")
    
    previous_status = t.status
    if new_status == "APPROVED" and t.budget_item_id:
        budget = db.query(models.BudgetItem).filter(models.BudgetItem.id == t.budget_item_id).first()
        if budget:
            budget.remaining_budget = (budget.remaining_budget or budget.allocated_1403 or 0) - (t.amount or 0)
            budget.reserved_amount = (budget.reserved_amount or 0) - (t.amount or 0)
            budget.spent_1403 = (budget.spent_1403 or 0) + (t.amount or 0)
    
    t.status = new_status
    t.current_approval_level = admin_level
    t.reviewed_by_id = current_user.id
    t.reviewed_at = datetime.utcnow()
    
    db.add(models.WorkflowLog(transaction_id=t.id, admin_id=current_user.id, admin_level=admin_level, action="APPROVE", previous_status=previous_status, new_status=new_status))
    db.commit()
    return {"status": "success", "message": f"تراکنش تایید شد و به وضعیت {new_status} رفت", "new_status": new_status}

@router.post("/transactions/{transaction_id}/reject")
def admin_reject_transaction(transaction_id: int, data: RejectWithReasonRequest, request: Request, db: Session = Depends(get_db)):
    """Reject transaction with reason"""
    current_user = get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    if not current_user.role.startswith("ADMIN_L") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    
    t = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
    
    if t.status not in ["PENDING_L1", "PENDING_L2", "PENDING_L3", "PENDING_L4", "pending"]:
        raise HTTPException(status_code=400, detail=f"تراکنش در وضعیت {t.status} قابل رد نیست")
    
    previous_status = t.status
    admin_level = current_user.admin_level or (4 if current_user.role == "admin" else 1)
    
    if t.budget_item_id:
        budget = db.query(models.BudgetItem).filter(models.BudgetItem.id == t.budget_item_id).first()
        if budget:
            budget.reserved_amount = (budget.reserved_amount or 0) - (t.amount or 0)
    
    new_status = "DRAFT" if data.return_to_user else "REJECTED"
    action = "RETURN" if data.return_to_user else "REJECT"
    
    t.status = new_status
    t.reviewed_by_id = current_user.id
    t.reviewed_at = datetime.utcnow()
    t.rejection_reason = data.reason
    
    db.add(models.WorkflowLog(transaction_id=t.id, admin_id=current_user.id, admin_level=admin_level, action=action, comment=data.reason, previous_status=previous_status, new_status=new_status))
    db.commit()
    return {"status": "success", "message": "تراکنش به کاربر برگشت داده شد" if data.return_to_user else "تراکنش رد شد", "new_status": new_status}
