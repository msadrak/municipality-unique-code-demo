"""
Admin Router - Transaction management with 4-level workflow
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, case
from pydantic import BaseModel
from typing import Optional
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


# ============================================================
# GET /admin/inbox — Items pending for the current user's level
# ============================================================

def _require_admin(request: Request, db: Session):
    """Get authenticated admin user or raise."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    if user.role != "admin" and not (user.role or "").startswith("ADMIN_L"):
        raise HTTPException(status_code=403, detail="فقط ادمین دسترسی دارد")
    return user


def _serialize_transaction(t: models.Transaction, db: Session) -> dict:
    """Convert a Transaction ORM instance to a JSON-safe dict."""
    zone = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.zone_id).first() if t.zone_id else None
    dept = db.query(models.OrgUnit).filter(models.OrgUnit.id == t.department_id).first() if t.department_id else None
    budget = db.query(models.BudgetItem).filter(models.BudgetItem.id == t.budget_item_id).first() if t.budget_item_id else None
    creator = db.query(models.User).filter(models.User.id == t.created_by_id).first() if t.created_by_id else None
    return {
        "id": t.id,
        "unique_code": t.unique_code,
        "status": t.status,
        "current_approval_level": t.current_approval_level,
        "beneficiary_name": t.beneficiary_name,
        "amount": t.amount,
        "description": t.description,
        "contract_number": t.contract_number,
        "zone_title": zone.title if zone else "-",
        "dept_title": dept.title if dept else "-",
        "budget_code": budget.budget_code if budget else "-",
        "budget_description": budget.description if budget else "-",
        "created_by_name": creator.full_name if creator else "-",
        "rejection_reason": t.rejection_reason,
        "created_at": t.created_at.strftime("%Y/%m/%d %H:%M") if t.created_at else None,
    }


def _serialize_contract(c: models.Contract, db: Session) -> dict:
    """Convert a Contract ORM instance to a JSON-safe dict."""
    status_val = c.status.value if isinstance(c.status, models.ContractStatus) else str(c.status)
    contractor = c.contractor.company_name if c.contractor else "-"
    org = db.query(models.OrgUnit).filter(models.OrgUnit.id == c.org_unit_id).first() if c.org_unit_id else None
    return {
        "id": c.id,
        "entity_type": "CONTRACT",
        "contract_number": c.contract_number,
        "title": c.title,
        "status": status_val,
        "contractor_name": contractor,
        "total_amount": c.total_amount,
        "paid_amount": c.paid_amount or 0,
        "org_unit_title": org.title if org else "-",
        "created_at": c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else None,
    }


@router.get("/inbox")
def admin_inbox(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = Query(None, description="TRANSACTION or CONTRACT"),
    db: Session = Depends(get_db),
):
    """
    Inbox: return items pending for the requesting user's approval level.

    For ADMIN_L1 → items with status PENDING_L1
    For ADMIN_L2 → items with status PENDING_L2
    etc.

    Includes both Transactions and Contracts (where applicable).
    """
    user = _require_admin(request, db)
    admin_level = user.admin_level or 0

    # Super-admin (role="admin") sees all pending items
    if user.role == "admin":
        pending_statuses = ["PENDING_L1", "PENDING_L2", "PENDING_L3", "PENDING_L4"]
    elif 1 <= admin_level <= 4:
        pending_statuses = [f"PENDING_L{admin_level}"]
    else:
        pending_statuses = []

    items = []

    # --- Transactions ---
    if entity_type is None or entity_type == "TRANSACTION":
        tx_query = (
            db.query(models.Transaction)
            .filter(models.Transaction.status.in_(pending_statuses))
            .order_by(models.Transaction.created_at.desc())
        )
        tx_total = tx_query.count()
        offset = (page - 1) * limit
        for t in tx_query.offset(offset).limit(limit).all():
            row = _serialize_transaction(t, db)
            row["entity_type"] = "TRANSACTION"
            items.append(row)
    else:
        tx_total = 0

    # --- Contracts pending approval ---
    if entity_type is None or entity_type == "CONTRACT":
        contract_query = (
            db.query(models.Contract)
            .filter(models.Contract.status == models.ContractStatus.PENDING_APPROVAL)
            .order_by(models.Contract.created_at.desc())
        )
        contract_total = contract_query.count()
        for c in contract_query.all():
            items.append(_serialize_contract(c, db))
    else:
        contract_total = 0

    return {
        "items": items,
        "total_transactions": tx_total,
        "total_contracts": contract_total,
        "admin_level": admin_level,
        "admin_role": user.role,
        "page": page,
        "limit": limit,
    }


# ============================================================
# GET /admin/overview — All active items with workflow state
# ============================================================

@router.get("/overview")
def admin_overview(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    System overview: active Transactions and Contracts with their current
    workflow state for the visual dashboard.
    """
    user = _require_admin(request, db)

    active_statuses = [
        "DRAFT", "PENDING_L1", "PENDING_L2", "PENDING_L3", "PENDING_L4",
        "APPROVED", "BOOKED",
    ]

    offset = (page - 1) * limit
    tx_query = (
        db.query(models.Transaction)
        .filter(models.Transaction.status.in_(active_statuses))
        .order_by(models.Transaction.created_at.desc())
    )
    total = tx_query.count()
    transactions = []
    for t in tx_query.offset(offset).limit(limit).all():
        row = _serialize_transaction(t, db)
        row["entity_type"] = "TRANSACTION"
        transactions.append(row)

    contract_statuses = [
        models.ContractStatus.DRAFT,
        models.ContractStatus.PENDING_APPROVAL,
        models.ContractStatus.APPROVED,
        models.ContractStatus.IN_PROGRESS,
        models.ContractStatus.PENDING_COMPLETION,
    ]
    contracts = []
    for c in (
        db.query(models.Contract)
        .filter(models.Contract.status.in_(contract_statuses))
        .order_by(models.Contract.created_at.desc())
        .limit(20)
        .all()
    ):
        contracts.append(_serialize_contract(c, db))

    return {
        "transactions": transactions,
        "contracts": contracts,
        "total_transactions": total,
        "total_contracts": len(contracts),
        "page": page,
        "limit": limit,
    }


# ============================================================
# GET /admin/stats — Aggregate counters for dashboard
# ============================================================

@router.get("/stats")
def admin_stats(request: Request, db: Session = Depends(get_db)):
    """Aggregate counters for the admin command-center dashboard."""
    user = _require_admin(request, db)
    admin_level = user.admin_level or 0

    tx_counts = dict(
        db.query(models.Transaction.status, func.count(models.Transaction.id))
        .group_by(models.Transaction.status)
        .all()
    )

    contract_counts = {}
    for row in (
        db.query(models.Contract.status, func.count(models.Contract.id))
        .group_by(models.Contract.status)
        .all()
    ):
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        contract_counts[key] = row[1]

    my_pending = tx_counts.get(f"PENDING_L{admin_level}", 0) if 1 <= admin_level <= 4 else 0

    return {
        "transactions": {
            "total": sum(tx_counts.values()),
            "pending_l1": tx_counts.get("PENDING_L1", 0),
            "pending_l2": tx_counts.get("PENDING_L2", 0),
            "pending_l3": tx_counts.get("PENDING_L3", 0),
            "pending_l4": tx_counts.get("PENDING_L4", 0),
            "approved": tx_counts.get("APPROVED", 0),
            "rejected": tx_counts.get("REJECTED", 0),
            "booked": tx_counts.get("BOOKED", 0),
            "my_pending": my_pending,
        },
        "contracts": {
            "total": sum(contract_counts.values()),
            "draft": contract_counts.get("DRAFT", 0),
            "pending_approval": contract_counts.get("PENDING_APPROVAL", 0),
            "approved": contract_counts.get("APPROVED", 0),
            "in_progress": contract_counts.get("IN_PROGRESS", 0),
            "completed": contract_counts.get("COMPLETED", 0),
            "closed": contract_counts.get("CLOSED", 0),
        },
        "admin_level": admin_level,
    }
