"""
Credit Request Router - Stage 1 Gateway
========================================

Provides CRUD + state-transition endpoints for CreditRequest (درخواست تامین اعتبار).

State machine:
    DRAFT -> SUBMITTED -> APPROVED (terminal)
    DRAFT -> CANCELLED (terminal)
    SUBMITTED -> REJECTED (terminal)
    SUBMITTED -> CANCELLED (terminal)

Approval model: single admin approval, approver != creator.
Approver eligibility: admin_level >= MIN_CR_APPROVER_LEVEL (env var, default 1).
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional

from app import models
from app.models import CreditRequest, CreditRequestLog, CreditRequestStatus, OrgUnit, User
from app.schemas.credit_request import (
    CreditRequestCreate,
    CreditRequestApprove,
    CreditRequestReject,
    CreditRequestCancel,
    CreditRequestResponse,
    CreditRequestListItem,
    CreditRequestListResponse,
    CreditRequestActionResponse,
    CreditRequestLogEntry,
)
from app.routers.auth import get_current_user, get_db

router = APIRouter(prefix="/credit-requests", tags=["Credit Requests (Stage 1 Gateway)"])

# Configurable minimum admin level for CR approval
MIN_CR_APPROVER_LEVEL = int(os.getenv("MIN_CR_APPROVER_LEVEL", "1"))


# ============================================================
# Helpers
# ============================================================

def _generate_credit_request_code(db: Session, fiscal_year: str, zone_id: int) -> str:
    """Generate CR-<fiscal_year>-<zone_code>-<sequence> code."""
    zone = db.query(OrgUnit).filter(OrgUnit.id == zone_id).first()
    zone_code = (zone.code or str(zone_id)).zfill(2) if zone else str(zone_id).zfill(2)
    
    prefix = f"CR-{fiscal_year}-{zone_code}-"
    # Count existing CRs with this prefix to determine next sequence
    count = db.query(CreditRequest).filter(
        CreditRequest.credit_request_code.like(f"{prefix}%")
    ).count()
    sequence = str(count + 1).zfill(4)
    return f"{prefix}{sequence}"


def _cr_to_response(cr: CreditRequest, db: Session) -> CreditRequestResponse:
    """Convert CreditRequest model to response schema."""
    zone = db.query(OrgUnit).filter(OrgUnit.id == cr.zone_id).first() if cr.zone_id else None
    dept = db.query(OrgUnit).filter(OrgUnit.id == cr.department_id).first() if cr.department_id else None
    section = db.query(OrgUnit).filter(OrgUnit.id == cr.section_id).first() if cr.section_id else None
    creator = db.query(User).filter(User.id == cr.created_by_id).first() if cr.created_by_id else None
    reviewer = db.query(User).filter(User.id == cr.reviewed_by_id).first() if cr.reviewed_by_id else None
    
    return CreditRequestResponse(
        id=cr.id,
        credit_request_code=cr.credit_request_code,
        status=cr.status.value if isinstance(cr.status, CreditRequestStatus) else cr.status,
        zone_id=cr.zone_id,
        zone_title=zone.title if zone else None,
        department_id=cr.department_id,
        department_title=dept.title if dept else None,
        section_id=cr.section_id,
        section_title=section.title if section else None,
        budget_code=cr.budget_code,
        amount_requested=cr.amount_requested,
        amount_approved=cr.amount_approved,
        description=cr.description,
        fiscal_year=cr.fiscal_year,
        attachments=cr.attachments,
        form_data=cr.form_data,
        created_by_id=cr.created_by_id,
        created_by_name=creator.full_name if creator else None,
        reviewed_by_id=cr.reviewed_by_id,
        reviewed_by_name=reviewer.full_name if reviewer else None,
        reviewed_at=cr.reviewed_at.strftime("%Y/%m/%d %H:%M") if cr.reviewed_at else None,
        rejection_reason=cr.rejection_reason,
        used_transaction_id=cr.used_transaction_id,
        version=cr.version,
        created_at=cr.created_at.strftime("%Y/%m/%d %H:%M") if cr.created_at else None,
        updated_at=cr.updated_at.strftime("%Y/%m/%d %H:%M") if cr.updated_at else None,
    )


def _add_log(db: Session, cr: CreditRequest, actor_id: int, action: str,
             prev_status: str, new_status: str, comment: str = None):
    """Append an audit log entry."""
    db.add(CreditRequestLog(
        credit_request_id=cr.id,
        actor_id=actor_id,
        action=action,
        previous_status=prev_status,
        new_status=new_status,
        comment=comment,
    ))


def _require_auth(request: Request, db: Session) -> User:
    """Get authenticated user or raise 401."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user


def _get_cr(db: Session, cr_id: int) -> CreditRequest:
    """Fetch CR by id or raise 404."""
    cr = db.query(CreditRequest).filter(CreditRequest.id == cr_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="درخواست تامین اعتبار یافت نشد")
    return cr


# ============================================================
# POST /credit-requests — create DRAFT
# ============================================================

@router.post("", response_model=CreditRequestResponse)
def create_credit_request(
    data: CreditRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new DRAFT credit request."""
    user = _require_auth(request, db)
    
    # Validate zone exists
    zone = db.query(OrgUnit).filter(OrgUnit.id == data.zone_id).first()
    if not zone:
        raise HTTPException(status_code=422, detail="منطقه یافت نشد")
    
    # Idempotency check
    if data.client_request_id:
        existing = db.query(CreditRequest).filter(
            CreditRequest.created_by_id == user.id,
            CreditRequest.client_request_id == data.client_request_id,
        ).first()
        if existing:
            return _cr_to_response(existing, db)
    
    code = _generate_credit_request_code(db, data.fiscal_year, data.zone_id)
    
    cr = CreditRequest(
        credit_request_code=code,
        status=CreditRequestStatus.DRAFT,
        created_by_id=user.id,
        zone_id=data.zone_id,
        department_id=data.department_id,
        section_id=data.section_id,
        budget_code=data.budget_code,
        amount_requested=data.amount_requested,
        description=data.description,
        fiscal_year=data.fiscal_year,
        attachments=data.attachments,
        form_data=data.form_data,
        client_request_id=data.client_request_id,
    )
    db.add(cr)
    db.flush()
    
    _add_log(db, cr, user.id, "CREATE", "", CreditRequestStatus.DRAFT.value)
    db.commit()
    db.refresh(cr)
    
    return _cr_to_response(cr, db)


# ============================================================
# POST /credit-requests/{id}/submit
# ============================================================

@router.post("/{cr_id}/submit", response_model=CreditRequestActionResponse)
def submit_credit_request(
    cr_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submit a DRAFT credit request for approval."""
    user = _require_auth(request, db)
    cr = _get_cr(db, cr_id)
    
    # Only creator can submit
    if cr.created_by_id != user.id:
        raise HTTPException(status_code=403, detail="فقط ایجادکننده می‌تواند ارسال کند")
    
    status_val = cr.status.value if isinstance(cr.status, CreditRequestStatus) else cr.status
    if status_val != CreditRequestStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail=f"درخواست در وضعیت {status_val} قابل ارسال نیست (فقط DRAFT)"
        )
    
    prev = status_val
    cr.status = CreditRequestStatus.SUBMITTED
    cr.version += 1
    _add_log(db, cr, user.id, "SUBMIT", prev, CreditRequestStatus.SUBMITTED.value)
    db.commit()
    
    return CreditRequestActionResponse(
        status="success",
        message="درخواست تامین اعتبار ارسال شد",
        new_status=CreditRequestStatus.SUBMITTED.value,
        credit_request_code=cr.credit_request_code,
    )


# ============================================================
# POST /credit-requests/{id}/approve
# ============================================================

@router.post("/{cr_id}/approve", response_model=CreditRequestActionResponse)
def approve_credit_request(
    cr_id: int,
    data: CreditRequestApprove,
    request: Request,
    db: Session = Depends(get_db),
):
    """Approve a SUBMITTED credit request. Single-level approval."""
    user = _require_auth(request, db)
    cr = _get_cr(db, cr_id)
    
    # Authorization: must be admin with sufficient level
    admin_level = user.admin_level or 0
    is_admin_role = user.role == "admin" or (user.role.startswith("ADMIN_L") and admin_level >= MIN_CR_APPROVER_LEVEL)
    if not is_admin_role:
        raise HTTPException(status_code=403, detail="سطح دسترسی ادمین کافی نیست")
    
    # Self-approval forbidden
    if cr.created_by_id == user.id:
        raise HTTPException(status_code=403, detail="تایید درخواست توسط ایجادکننده مجاز نیست")
    
    status_val = cr.status.value if isinstance(cr.status, CreditRequestStatus) else cr.status
    if status_val != CreditRequestStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"درخواست در وضعیت {status_val} قابل تایید نیست (فقط SUBMITTED)"
        )
    
    # Set approved amount
    approved_amount = data.amount_approved if data.amount_approved is not None else cr.amount_requested
    if approved_amount <= 0 or approved_amount > cr.amount_requested:
        raise HTTPException(
            status_code=422,
            detail=f"مبلغ تایید شده باید بین 0 و {cr.amount_requested:,.0f} ریال باشد"
        )
    
    prev = status_val
    cr.status = CreditRequestStatus.APPROVED
    cr.amount_approved = approved_amount
    cr.reviewed_by_id = user.id
    cr.reviewed_at = datetime.utcnow()
    cr.version += 1
    
    _add_log(db, cr, user.id, "APPROVE", prev, CreditRequestStatus.APPROVED.value, data.comment)
    db.commit()
    
    return CreditRequestActionResponse(
        status="success",
        message="درخواست تامین اعتبار تایید شد",
        new_status=CreditRequestStatus.APPROVED.value,
        credit_request_code=cr.credit_request_code,
    )


# ============================================================
# POST /credit-requests/{id}/reject
# ============================================================

@router.post("/{cr_id}/reject", response_model=CreditRequestActionResponse)
def reject_credit_request(
    cr_id: int,
    data: CreditRequestReject,
    request: Request,
    db: Session = Depends(get_db),
):
    """Reject a SUBMITTED credit request."""
    user = _require_auth(request, db)
    cr = _get_cr(db, cr_id)
    
    # Authorization
    admin_level = user.admin_level or 0
    is_admin_role = user.role == "admin" or (user.role.startswith("ADMIN_L") and admin_level >= MIN_CR_APPROVER_LEVEL)
    if not is_admin_role:
        raise HTTPException(status_code=403, detail="سطح دسترسی ادمین کافی نیست")
    
    status_val = cr.status.value if isinstance(cr.status, CreditRequestStatus) else cr.status
    if status_val != CreditRequestStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"درخواست در وضعیت {status_val} قابل رد نیست (فقط SUBMITTED)"
        )
    
    prev = status_val
    cr.status = CreditRequestStatus.REJECTED
    cr.rejection_reason = data.reason
    cr.reviewed_by_id = user.id
    cr.reviewed_at = datetime.utcnow()
    cr.version += 1
    
    _add_log(db, cr, user.id, "REJECT", prev, CreditRequestStatus.REJECTED.value, data.reason)
    db.commit()
    
    return CreditRequestActionResponse(
        status="success",
        message="درخواست تامین اعتبار رد شد",
        new_status=CreditRequestStatus.REJECTED.value,
        credit_request_code=cr.credit_request_code,
    )


# ============================================================
# POST /credit-requests/{id}/cancel
# ============================================================

@router.post("/{cr_id}/cancel", response_model=CreditRequestActionResponse)
def cancel_credit_request(
    cr_id: int,
    data: CreditRequestCancel,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cancel a DRAFT or SUBMITTED credit request. Creator only."""
    user = _require_auth(request, db)
    cr = _get_cr(db, cr_id)
    
    if cr.created_by_id != user.id:
        raise HTTPException(status_code=403, detail="فقط ایجادکننده می‌تواند لغو کند")
    
    status_val = cr.status.value if isinstance(cr.status, CreditRequestStatus) else cr.status
    allowed = {CreditRequestStatus.DRAFT.value, CreditRequestStatus.SUBMITTED.value}
    if status_val not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"درخواست در وضعیت {status_val} قابل لغو نیست (فقط DRAFT یا SUBMITTED)"
        )
    
    prev = status_val
    cr.status = CreditRequestStatus.CANCELLED
    cr.version += 1
    
    _add_log(db, cr, user.id, "CANCEL", prev, CreditRequestStatus.CANCELLED.value, data.reason)
    db.commit()
    
    return CreditRequestActionResponse(
        status="success",
        message="درخواست تامین اعتبار لغو شد",
        new_status=CreditRequestStatus.CANCELLED.value,
        credit_request_code=cr.credit_request_code,
    )


# ============================================================
# GET /credit-requests — list with filters
# ============================================================

@router.get("", response_model=CreditRequestListResponse)
def list_credit_requests(
    request: Request,
    zone_id: Optional[int] = None,
    department_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status: Optional[str] = None,
    fiscal_year: Optional[str] = None,
    budget_code: Optional[str] = None,
    mine_only: bool = Query(False, description="Show only my CRs"),
    available_only: bool = Query(False, description="APPROVED + unused only"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List credit requests with filters."""
    user = _require_auth(request, db)
    
    query = db.query(CreditRequest)
    
    if mine_only:
        query = query.filter(CreditRequest.created_by_id == user.id)
    if zone_id:
        query = query.filter(CreditRequest.zone_id == zone_id)
    if department_id:
        query = query.filter(CreditRequest.department_id == department_id)
    if section_id:
        query = query.filter(CreditRequest.section_id == section_id)
    if status:
        query = query.filter(CreditRequest.status == status)
    if fiscal_year:
        query = query.filter(CreditRequest.fiscal_year == fiscal_year)
    if budget_code:
        query = query.filter(CreditRequest.budget_code == budget_code)
    if available_only:
        query = query.filter(
            CreditRequest.status == CreditRequestStatus.APPROVED,
            CreditRequest.used_transaction_id.is_(None),
        )
    
    total = query.count()
    offset = (page - 1) * limit
    crs = query.order_by(CreditRequest.created_at.desc()).offset(offset).limit(limit).all()
    
    items = []
    for cr in crs:
        zone = db.query(OrgUnit).filter(OrgUnit.id == cr.zone_id).first() if cr.zone_id else None
        creator = db.query(User).filter(User.id == cr.created_by_id).first() if cr.created_by_id else None
        status_str = cr.status.value if isinstance(cr.status, CreditRequestStatus) else cr.status
        items.append(CreditRequestListItem(
            id=cr.id,
            credit_request_code=cr.credit_request_code,
            status=status_str,
            zone_title=zone.title if zone else None,
            budget_code=cr.budget_code,
            amount_requested=cr.amount_requested,
            amount_approved=cr.amount_approved,
            description=cr.description,
            created_by_name=creator.full_name if creator else None,
            used_transaction_id=cr.used_transaction_id,
            created_at=cr.created_at.strftime("%Y/%m/%d %H:%M") if cr.created_at else None,
        ))
    
    return CreditRequestListResponse(items=items, total=total, page=page, limit=limit)


# ============================================================
# GET /credit-requests/{id} — detail
# ============================================================

@router.get("/{cr_id}", response_model=CreditRequestResponse)
def get_credit_request(
    cr_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get credit request detail by id."""
    _require_auth(request, db)
    cr = _get_cr(db, cr_id)
    return _cr_to_response(cr, db)


# ============================================================
# GET /credit-requests/{id}/logs — audit trail
# ============================================================

@router.get("/{cr_id}/logs", response_model=list[CreditRequestLogEntry])
def get_credit_request_logs(
    cr_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get audit trail for a credit request."""
    _require_auth(request, db)
    _get_cr(db, cr_id)  # ensure exists
    
    logs = db.query(CreditRequestLog).filter(
        CreditRequestLog.credit_request_id == cr_id
    ).order_by(CreditRequestLog.created_at.asc()).all()
    
    result = []
    for log in logs:
        actor = db.query(User).filter(User.id == log.actor_id).first()
        result.append(CreditRequestLogEntry(
            id=log.id,
            action=log.action,
            previous_status=log.previous_status,
            new_status=log.new_status,
            actor_name=actor.full_name if actor else None,
            comment=log.comment,
            created_at=log.created_at.strftime("%Y/%m/%d %H:%M") if log.created_at else None,
        ))
    return result
