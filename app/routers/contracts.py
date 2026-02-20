"""
Contract Lifecycle Router - Sprint 2
======================================

Provides the Contract Wizard API endpoints for creating and managing contracts.

Endpoints:
  POST /contracts/draft           — Start wizard (create draft with budget reservation)
  GET  /contracts                 — List contracts (paginated, filterable by status)
  GET  /contracts/{id}            — Contract detail
  GET  /contracts/{id}/render     — Merged JSON Schema + current data (for frontend form)
  PUT  /contracts/{id}/submit     — Move status DRAFT → PENDING_APPROVAL
  PUT  /contracts/{id}/transition — Explicit status transition (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.models import Contract, ContractStatus, Contractor, ContractTemplate
from app.schemas.contract import (
    ContractDraftCreate,
    ContractResponse,
    ContractListItem,
    ContractListResponse,
    ContractRenderResponse,
    ContractStatusTransition,
)
from app.services.contract_service import (
    create_draft,
    transition_status,
    render_contract,
    ContractNotFoundError,
    InvalidTransitionError,
    ContractValidationError,
)
from app.services.budget_service import InsufficientFundsError
from app.routers.auth import get_current_user, get_db

router = APIRouter(prefix="/contracts", tags=["Contracts"])


# ============================================================
# Helpers
# ============================================================

def _require_auth(request: Request, db: Session):
    """Get authenticated user or raise 401."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user


def _contract_to_response(c: Contract) -> ContractResponse:
    """Convert Contract ORM model to Pydantic response."""
    status_val = c.status.value if isinstance(c.status, ContractStatus) else c.status
    return ContractResponse(
        id=c.id,
        contract_number=c.contract_number,
        title=c.title,
        status=status_val,
        contractor_id=c.contractor_id,
        contractor_name=c.contractor.company_name if c.contractor else None,
        template_id=c.template_id,
        template_title=c.template.title if c.template else None,
        budget_row_id=c.budget_row_id,
        credit_request_id=c.credit_request_id,
        org_unit_id=c.org_unit_id,
        total_amount=c.total_amount,
        paid_amount=c.paid_amount or 0,
        start_date=str(c.start_date) if c.start_date else None,
        end_date=str(c.end_date) if c.end_date else None,
        template_data=c.template_data,
        metadata_extra=c.metadata_extra,
        created_by_id=c.created_by_id,
        created_at=c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else None,
        updated_at=c.updated_at.strftime("%Y/%m/%d %H:%M") if c.updated_at else None,
        version=c.version or 1,
    )


def _contract_to_list_item(c: Contract) -> ContractListItem:
    """Convert Contract ORM model to list item."""
    status_val = c.status.value if isinstance(c.status, ContractStatus) else c.status
    return ContractListItem(
        id=c.id,
        contract_number=c.contract_number,
        title=c.title,
        status=status_val,
        contractor_name=c.contractor.company_name if c.contractor else None,
        total_amount=c.total_amount,
        paid_amount=c.paid_amount or 0,
        created_at=c.created_at.strftime("%Y/%m/%d %H:%M") if c.created_at else None,
    )


# ============================================================
# POST /contracts/draft — Start wizard
# ============================================================

@router.post("/draft", response_model=ContractResponse)
def create_contract_draft(
    data: ContractDraftCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a new contract draft (wizard step 1).
    
    Validates budget availability, reserves funds via Credit System (ACL),
    blocks budget in BudgetRow, and returns the new contract in DRAFT status.
    """
    user = _require_auth(request, db)

    try:
        contract = create_draft(
            db=db,
            budget_row_id=data.budget_row_id,
            contractor_id=data.contractor_id,
            template_id=data.template_id,
            title=data.title,
            total_amount=data.total_amount,
            user_id=user.id,
            template_data=data.template_data,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        db.commit()
        db.refresh(contract)
        return _contract_to_response(contract)

    except ContractValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except InsufficientFundsError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"خطای سرور: {str(e)}")


# ============================================================
# GET /contracts — List
# ============================================================

@router.get("", response_model=ContractListResponse)
def list_contracts(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, PENDING_APPROVAL, ...)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List contracts with optional status filter."""
    _require_auth(request, db)

    query = db.query(Contract)

    if status:
        try:
            status_enum = ContractStatus(status)
            query = query.filter(Contract.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"وضعیت نامعتبر: {status}")

    total = query.count()
    offset = (page - 1) * limit
    contracts = (
        query.order_by(Contract.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [_contract_to_list_item(c) for c in contracts]
    return ContractListResponse(items=items, total=total, page=page, limit=limit)


# ============================================================
# GET /contracts/{id} — Detail
# ============================================================

@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get contract detail by ID."""
    _require_auth(request, db)

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="قرارداد یافت نشد")

    return _contract_to_response(contract)


# ============================================================
# GET /contracts/{id}/render — Template + Data merge
# ============================================================

@router.get("/{contract_id}/render", response_model=ContractRenderResponse)
def render_contract_form(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Return the JSON Schema of the template merged with the contract's current data.
    
    The frontend uses this to render the dynamic form in the contract wizard.
    """
    _require_auth(request, db)

    try:
        result = render_contract(db, contract_id)
        return ContractRenderResponse(**result)
    except ContractNotFoundError:
        raise HTTPException(status_code=404, detail="قرارداد یافت نشد")
    except ContractValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ============================================================
# PUT /contracts/{id}/submit — DRAFT → PENDING_APPROVAL
# ============================================================

@router.put("/{contract_id}/submit", response_model=ContractResponse)
def submit_contract(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Submit the contract for approval (DRAFT → PENDING_APPROVAL).
    
    This is a convenience endpoint for the wizard's final step.
    """
    user = _require_auth(request, db)

    try:
        contract = transition_status(
            db=db,
            contract_id=contract_id,
            new_status=ContractStatus.PENDING_APPROVAL.value,
            user_id=user.id,
        )
        db.commit()
        db.refresh(contract)
        return _contract_to_response(contract)
    except ContractNotFoundError:
        raise HTTPException(status_code=404, detail="قرارداد یافت نشد")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ============================================================
# PUT /contracts/{id}/transition — Generic status transition
# ============================================================

@router.put("/{contract_id}/transition", response_model=ContractResponse)
def transition_contract(
    contract_id: int,
    data: ContractStatusTransition,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Transition a contract to a new status (admin operation).
    
    Enforces the state machine and triggers side effects
    (e.g., budget lock on APPROVED, budget release on REJECTED).
    """
    user = _require_auth(request, db)

    try:
        contract = transition_status(
            db=db,
            contract_id=contract_id,
            new_status=data.new_status,
            user_id=user.id,
        )
        db.commit()
        db.refresh(contract)
        return _contract_to_response(contract)
    except ContractNotFoundError:
        raise HTTPException(status_code=404, detail="قرارداد یافت نشد")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"خطای سرور: {str(e)}")
