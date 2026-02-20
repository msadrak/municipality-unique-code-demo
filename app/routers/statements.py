"""
Progress Statement Router - Sprint 3
====================================

Endpoints:
- POST /contracts/{id}/statements
- GET /contracts/{id}/statements
- GET /contracts/{id}/statements/summary
- GET /statements/{id}
- PUT /statements/{id}/submit
- PUT /statements/{id}/approve
- PUT /statements/{id}/pay
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.models import ProgressStatement, ProgressStatementStatus
from app.routers.auth import get_current_user, get_db
from app.schemas.statement import (
    StatementApprove,
    StatementCreate,
    StatementFinancialSummary,
    StatementListItem,
    StatementListResponse,
    StatementResponse,
)
from app.services.budget_service import InvalidOperationError
from app.services.statement_service import (
    InvalidStatementTransitionError,
    OverPaymentError,
    StatementNotFoundError,
    StatementValidationError,
    approve_statement,
    create_statement,
    get_contract_statements,
    get_statement_financial_summary,
    pay_statement,
    submit_statement,
)

router = APIRouter(tags=["Progress Statements"])


def _require_auth(request: Request, db: Session):
    """Get authenticated user or raise 401."""
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _fmt_dt(value):
    return value.strftime("%Y/%m/%d %H:%M") if value else None


def _statement_to_response(statement: ProgressStatement) -> StatementResponse:
    status_val = (
        statement.status.value
        if isinstance(statement.status, ProgressStatementStatus)
        else statement.status
    )
    return StatementResponse(
        id=statement.id,
        statement_number=statement.statement_number,
        contract_id=statement.contract_id,
        sequence_number=statement.sequence_number,
        statement_type=statement.statement_type or "INTERIM",
        status=status_val,
        description=statement.description,
        period_start=str(statement.period_start) if statement.period_start else None,
        period_end=str(statement.period_end) if statement.period_end else None,
        gross_amount=statement.gross_amount,
        deductions=statement.deductions or 0,
        net_amount=statement.net_amount,
        cumulative_amount=statement.cumulative_amount or 0,
        submitted_by_id=statement.submitted_by_id,
        reviewed_by_id=statement.reviewed_by_id,
        review_comment=statement.review_comment,
        submitted_at=_fmt_dt(statement.submitted_at),
        reviewed_at=_fmt_dt(statement.reviewed_at),
        created_at=_fmt_dt(statement.created_at),
        updated_at=_fmt_dt(statement.updated_at),
        version=statement.version or 1,
    )


def _statement_to_list_item(statement: ProgressStatement) -> StatementListItem:
    status_val = (
        statement.status.value
        if isinstance(statement.status, ProgressStatementStatus)
        else statement.status
    )
    return StatementListItem(
        id=statement.id,
        statement_number=statement.statement_number,
        sequence_number=statement.sequence_number,
        status=status_val,
        net_amount=statement.net_amount,
        cumulative_amount=statement.cumulative_amount or 0,
        created_at=_fmt_dt(statement.created_at),
    )


@router.post("/contracts/{contract_id}/statements", response_model=StatementResponse)
def create_progress_statement(
    contract_id: int,
    data: StatementCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new draft progress statement for a contract."""
    user = _require_auth(request, db)

    try:
        statement = create_statement(
            db=db,
            contract_id=contract_id,
            description=data.description,
            user_id=user.id,
            amount=data.amount,
            gross_amount=data.gross_amount,
            deductions=data.deductions,
            period_start=data.period_start,
            period_end=data.period_end,
            statement_type=data.statement_type,
        )
        db.commit()
        db.refresh(statement)
        return _statement_to_response(statement)
    except OverPaymentError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except StatementValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {exc}")


@router.get("/contracts/{contract_id}/statements", response_model=StatementListResponse)
def list_contract_statements(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """List all statements for a contract."""
    _require_auth(request, db)
    statements = get_contract_statements(db, contract_id)
    items = [_statement_to_list_item(item) for item in statements]
    return StatementListResponse(items=items, total=len(items), contract_id=contract_id)


@router.get(
    "/contracts/{contract_id}/statements/summary",
    response_model=StatementFinancialSummary,
)
def contract_statement_summary(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get aggregated financial summary for statements of a contract."""
    _require_auth(request, db)
    try:
        return StatementFinancialSummary(**get_statement_financial_summary(db, contract_id))
    except StatementValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/statements/{statement_id}", response_model=StatementResponse)
def get_statement(
    statement_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get statement detail by ID."""
    _require_auth(request, db)
    statement = (
        db.query(ProgressStatement)
        .filter(ProgressStatement.id == statement_id)
        .first()
    )
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
    return _statement_to_response(statement)


@router.put("/statements/{statement_id}/submit", response_model=StatementResponse)
def submit_progress_statement(
    statement_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submit a draft statement."""
    user = _require_auth(request, db)
    try:
        statement = submit_statement(db, statement_id, user.id)
        db.commit()
        db.refresh(statement)
        return _statement_to_response(statement)
    except StatementNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Statement not found")
    except InvalidStatementTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))


@router.put("/statements/{statement_id}/approve", response_model=StatementResponse)
def approve_progress_statement(
    statement_id: int,
    data: StatementApprove,
    request: Request,
    db: Session = Depends(get_db),
):
    """Approve a submitted statement."""
    user = _require_auth(request, db)
    try:
        statement = approve_statement(
            db=db,
            statement_id=statement_id,
            user_id=user.id,
            review_comment=data.review_comment,
        )
        db.commit()
        db.refresh(statement)
        return _statement_to_response(statement)
    except StatementNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Statement not found")
    except InvalidStatementTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))


@router.put("/statements/{statement_id}/pay", response_model=StatementResponse)
def pay_progress_statement(
    statement_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Finalize payment for an approved statement.

    Budget side effect:
    - confirm_spend() converts blocked -> spent
    """
    user = _require_auth(request, db)
    try:
        statement = pay_statement(db, statement_id, user.id)
        db.commit()
        db.refresh(statement)
        return _statement_to_response(statement)
    except StatementNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Statement not found")
    except StatementValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except InvalidStatementTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOperationError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {exc}")
