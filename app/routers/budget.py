"""
Budget Control API Router - The "Sentinel" Pattern
====================================================

Exposes atomic budget operations with proper error handling
and concurrency-safe database access.

Endpoints:
- GET  /budget/check/{activity_id}  - Pre-flight budget availability check
- GET  /budget/row/{budget_row_id}  - Direct budget row lookup
- POST /budget/block               - Reserve funds for pending request
- POST /budget/release             - Release blocked funds (rejection)
- POST /budget/confirm             - Confirm spend (approval)
- GET  /budget/transactions/{budget_row_id} - Transaction history
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import BudgetRow, BudgetTransaction, SubsystemActivity, OperationType
from app.services.budget_service import (
    block_funds,
    release_funds,
    confirm_spend,
    get_budget_status,
    get_transaction_history,
    InsufficientFundsError,
    InvalidOperationError,
)
from app.schemas.budget import (
    BudgetStatus,
    TransactionStatus,
    BlockFundsRequest,
    ReleaseFundsRequest,
    ConfirmSpendRequest,
    BudgetCheckResponse,
    BudgetTransactionResponse,
    BudgetListResponse,
    InsufficientFundsResponse,
    BudgetNotFoundResponse,
)


# ============================================================
# Router Configuration
# ============================================================

router = APIRouter(
    prefix="/budget",
    tags=["Budget Control"],
    responses={
        404: {"model": BudgetNotFoundResponse, "description": "Budget not found"},
        400: {"model": InsufficientFundsResponse, "description": "Insufficient funds"},
    }
)


# ============================================================
# Dependency Injection
# ============================================================

def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id() -> str:
    """
    Get current authenticated user ID.
    TODO: Replace with actual auth dependency.
    """
    # Placeholder - in production, extract from JWT token
    return "system_user"


# ============================================================
# Helper Functions
# ============================================================

def calculate_budget_status(approved: int, spent: int, blocked: int) -> BudgetStatus:
    """Determine budget status based on utilization."""
    remaining = approved - spent - blocked
    if remaining <= 0:
        return BudgetStatus.EXHAUSTED
    utilization = (spent + blocked) / approved if approved > 0 else 0
    if utilization >= 0.8:
        return BudgetStatus.LOW
    return BudgetStatus.AVAILABLE


def budget_row_to_response(row: BudgetRow, activity: Optional[SubsystemActivity] = None) -> BudgetCheckResponse:
    """Convert BudgetRow model to response schema."""
    remaining = row.remaining_balance
    utilization = ((row.spent_amount + row.blocked_amount) / row.approved_amount * 100) if row.approved_amount > 0 else 0
    
    return BudgetCheckResponse(
        budget_row_id=row.id,
        budget_code=row.budget_coding,
        description=row.description,
        activity_id=row.activity_id,
        activity_code=activity.code if activity else None,
        fiscal_year=row.fiscal_year,
        total_approved=row.approved_amount,
        total_blocked=row.blocked_amount,
        total_spent=row.spent_amount,
        remaining_available=remaining,
        status=calculate_budget_status(row.approved_amount, row.spent_amount, row.blocked_amount),
        utilization_percent=round(utilization, 2)
    )


# ============================================================
# Endpoints
# ============================================================

@router.get(
    "/check/{activity_id}",
    response_model=BudgetCheckResponse,
    summary="Pre-flight Budget Check by Activity",
    description="""
    Fetch the live budget status for a given activity.
    Use this when a user selects an activity in the UI.
    
    **Note:** If multiple budget rows exist for an activity, returns the first one.
    Use `/budget/list/{activity_id}` to get all budget rows.
    """
)
def check_budget_by_activity(
    activity_id: int,
    fiscal_year: str = Query("1403", description="Fiscal year to check"),
    db: Session = Depends(get_db)
):
    """Pre-flight check: Get budget availability for an activity."""
    
    # Find budget row for this activity
    budget_row = db.query(BudgetRow).filter(
        BudgetRow.activity_id == activity_id,
        BudgetRow.fiscal_year == fiscal_year
    ).first()
    
    if not budget_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "BUDGET_NOT_FOUND",
                "message": f"No budget allocated for activity ID {activity_id} in fiscal year {fiscal_year}"
            }
        )
    
    # Get activity info
    activity = db.query(SubsystemActivity).filter(
        SubsystemActivity.id == activity_id
    ).first()
    
    return budget_row_to_response(budget_row, activity)


@router.get(
    "/row/{budget_row_id}",
    response_model=BudgetCheckResponse,
    summary="Direct Budget Row Lookup",
    description="Fetch budget details by specific budget row ID."
)
def get_budget_row(
    budget_row_id: int,
    db: Session = Depends(get_db)
):
    """Direct lookup of a specific budget row."""
    
    budget_row = db.query(BudgetRow).filter(
        BudgetRow.id == budget_row_id
    ).first()
    
    if not budget_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "BUDGET_NOT_FOUND",
                "message": f"Budget row ID {budget_row_id} not found"
            }
        )
    
    activity = db.query(SubsystemActivity).filter(
        SubsystemActivity.id == budget_row.activity_id
    ).first()
    
    return budget_row_to_response(budget_row, activity)


@router.get(
    "/list/{activity_id}",
    response_model=BudgetListResponse,
    summary="List All Budget Rows for Activity",
    description="""
    Get all budget rows associated with an activity.
    
    **Zone-Based Filtering:**
    - If `zone_id` is provided, returns budgets for that zone OR global budgets (org_unit_id=NULL)
    - If `zone_id` is not provided, returns all budgets for the activity
    """
)
def list_budgets_by_activity(
    activity_id: int,
    zone_id: Optional[int] = Query(None, description="Filter by zone/org unit ID"),
    fiscal_year: Optional[str] = Query(None, description="Filter by fiscal year"),
    db: Session = Depends(get_db)
):
    """List all budget rows for an activity, optionally filtered by zone."""
    
    query = db.query(BudgetRow).filter(BudgetRow.activity_id == activity_id)
    
    # Zone-Based Filtering: Show zone-specific OR global budgets
    if zone_id:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                BudgetRow.org_unit_id == zone_id,
                BudgetRow.org_unit_id.is_(None)  # Global budgets
            )
        )
    
    if fiscal_year:
        query = query.filter(BudgetRow.fiscal_year == fiscal_year)
    
    budget_rows = query.all()
    
    # Get activity info
    activity = db.query(SubsystemActivity).filter(
        SubsystemActivity.id == activity_id
    ).first()
    
    return BudgetListResponse(
        budget_rows=[budget_row_to_response(row, activity) for row in budget_rows],
        total_count=len(budget_rows)
    )


@router.post(
    "/block",
    response_model=BudgetTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Block/Reserve Funds",
    description="""
    Atomically reserve funds for a pending request.
    
    This operation:
    1. Acquires a row-level lock on the budget row
    2. Checks if sufficient balance is available
    3. Increases `blocked_amount`
    4. Creates an audit trail entry
    
    **Concurrency Safe:** Uses SELECT FOR UPDATE to prevent race conditions.
    """,
    responses={
        400: {"model": InsufficientFundsResponse, "description": "Insufficient funds"}
    }
)
def block_budget_funds(
    request: BlockFundsRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Reserve funds for a pending request."""
    
    try:
        # Call atomic service
        transaction = block_funds(
            db=db,
            budget_id=request.budget_row_id,
            amount=request.amount,
            user_id=user_id,
            reference_doc=request.request_reference_id,
            notes=request.notes
        )
        
        # Commit the transaction
        db.commit()
        
        # Get budget row for response
        budget_row = db.query(BudgetRow).filter(
            BudgetRow.id == request.budget_row_id
        ).first()
        
        return BudgetTransactionResponse(
            transaction_id=transaction.id,
            budget_row_id=budget_row.id,
            budget_code=budget_row.budget_coding,
            status=TransactionStatus.BLOCKED,
            amount=transaction.amount,
            reference_doc=transaction.reference_doc,
            performed_by=transaction.performed_by,
            created_at=transaction.created_at,
            new_remaining_balance=budget_row.remaining_balance
        )
        
    except InsufficientFundsError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INSUFFICIENT_FUNDS",
                "message": str(e),
                "budget_row_id": e.budget_id,
                "requested_amount": e.requested_amount,
                "available_balance": e.available_balance
            }
        )
    except InvalidOperationError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_OPERATION", "message": str(e)}
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "DATABASE_ERROR", "message": "An unexpected database error occurred"}
        )


@router.post(
    "/release",
    response_model=BudgetTransactionResponse,
    summary="Release Blocked Funds",
    description="""
    Release previously blocked funds when a request is rejected.
    
    Provide the original BLOCK transaction ID. The system will:
    1. Look up the original transaction to get budget_id and amount
    2. Release the funds
    3. Create an audit trail entry
    """
)
def release_budget_funds(
    request: ReleaseFundsRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Release blocked funds (request rejected)."""
    
    # Look up the original BLOCK transaction
    original_tx = db.query(BudgetTransaction).filter(
        BudgetTransaction.id == request.transaction_id,
        BudgetTransaction.operation_type == OperationType.BLOCK
    ).first()
    
    if not original_tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "TRANSACTION_NOT_FOUND",
                "message": f"Block transaction ID {request.transaction_id} not found"
            }
        )
    
    try:
        # Call atomic service
        transaction = release_funds(
            db=db,
            budget_id=original_tx.budget_row_id,
            amount=original_tx.amount,
            user_id=user_id,
            reference_doc=original_tx.reference_doc,
            notes=request.notes
        )
        
        db.commit()
        
        # Get budget row for response
        budget_row = db.query(BudgetRow).filter(
            BudgetRow.id == original_tx.budget_row_id
        ).first()
        
        return BudgetTransactionResponse(
            transaction_id=transaction.id,
            budget_row_id=budget_row.id,
            budget_code=budget_row.budget_coding,
            status=TransactionStatus.RELEASED,
            amount=transaction.amount,
            reference_doc=transaction.reference_doc,
            performed_by=transaction.performed_by,
            created_at=transaction.created_at,
            new_remaining_balance=budget_row.remaining_balance
        )
        
    except InvalidOperationError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_OPERATION", "message": str(e)}
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "DATABASE_ERROR", "message": "An unexpected database error occurred"}
        )


@router.post(
    "/confirm",
    response_model=BudgetTransactionResponse,
    summary="Confirm Spend",
    description="""
    Confirm a payment: move funds from blocked to spent.
    
    Use this when a payment is approved and the check is signed.
    The funds will be moved from `blocked_amount` to `spent_amount`.
    """
)
def confirm_budget_spend(
    request: ConfirmSpendRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Confirm spending (payment approved)."""
    
    # Look up the original BLOCK transaction
    original_tx = db.query(BudgetTransaction).filter(
        BudgetTransaction.id == request.transaction_id,
        BudgetTransaction.operation_type == OperationType.BLOCK
    ).first()
    
    if not original_tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "TRANSACTION_NOT_FOUND",
                "message": f"Block transaction ID {request.transaction_id} not found"
            }
        )
    
    try:
        # Call atomic service
        transaction = confirm_spend(
            db=db,
            budget_id=original_tx.budget_row_id,
            amount=original_tx.amount,
            user_id=user_id,
            reference_doc=original_tx.reference_doc,
            notes=request.notes
        )
        
        db.commit()
        
        # Get budget row for response
        budget_row = db.query(BudgetRow).filter(
            BudgetRow.id == original_tx.budget_row_id
        ).first()
        
        return BudgetTransactionResponse(
            transaction_id=transaction.id,
            budget_row_id=budget_row.id,
            budget_code=budget_row.budget_coding,
            status=TransactionStatus.SPENT,
            amount=transaction.amount,
            reference_doc=transaction.reference_doc,
            performed_by=transaction.performed_by,
            created_at=transaction.created_at,
            new_remaining_balance=budget_row.remaining_balance
        )
        
    except InvalidOperationError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_OPERATION", "message": str(e)}
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "DATABASE_ERROR", "message": "An unexpected database error occurred"}
        )


@router.get(
    "/transactions/{budget_row_id}",
    response_model=List[BudgetTransactionResponse],
    summary="Transaction History",
    description="Get the audit trail for a budget row."
)
def get_budget_transactions(
    budget_row_id: int,
    limit: int = Query(100, le=500, description="Maximum transactions to return"),
    db: Session = Depends(get_db)
):
    """Get transaction history for a budget row."""
    
    # Verify budget row exists
    budget_row = db.query(BudgetRow).filter(
        BudgetRow.id == budget_row_id
    ).first()
    
    if not budget_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "BUDGET_NOT_FOUND",
                "message": f"Budget row ID {budget_row_id} not found"
            }
        )
    
    transactions = get_transaction_history(db, budget_row_id, limit)
    
    # Map operation types to status
    op_to_status = {
        OperationType.BLOCK: TransactionStatus.BLOCKED,
        OperationType.RELEASE: TransactionStatus.RELEASED,
        OperationType.SPEND: TransactionStatus.SPENT,
    }
    
    return [
        BudgetTransactionResponse(
            transaction_id=tx.id,
            budget_row_id=budget_row.id,
            budget_code=budget_row.budget_coding,
            status=op_to_status.get(tx.operation_type, TransactionStatus.BLOCKED),
            amount=tx.amount,
            reference_doc=tx.reference_doc,
            performed_by=tx.performed_by,
            created_at=tx.created_at,
            new_remaining_balance=tx.balance_after or 0
        )
        for tx in transactions
    ]
