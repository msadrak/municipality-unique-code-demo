"""
Budget Control Service - Zero Trust Implementation
===================================================

This module provides ACID-compliant budget operations with row-level locking.
All operations are atomic and create audit trail entries.

Key Principles:
1. SELECT FOR UPDATE: Prevents race conditions in concurrent access
2. Audit Trail: Every operation creates a BudgetTransaction record
3. Pre/Post Balance Snapshots: For forensic analysis
4. Fail-Safe: CHECK constraint at DB level prevents invalid states

Usage:
    from app.services.budget_service import block_funds, confirm_spend
    
    # Block funds for a pending request
    transaction = block_funds(
        db=session,
        budget_id=1,
        amount=1_000_000,
        user_id="user_123",
        reference_doc="Request-1024"
    )
    
    # Confirm spend when payment is approved
    transaction = confirm_spend(
        db=session,
        budget_id=1,
        amount=1_000_000,
        user_id="accountant_456",
        reference_doc="Request-1024"
    )
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from app.models import BudgetRow, BudgetTransaction, OperationType


# ============================================
# Custom Exceptions
# ============================================

class InsufficientFundsError(Exception):
    """
    Raised when a budget operation would exceed available balance.
    
    This is a critical business exception that must be caught and handled
    by the calling code (e.g., return error response to user).
    """
    def __init__(
        self,
        budget_id: int,
        requested_amount: int,
        available_balance: int,
        budget_coding: Optional[str] = None
    ):
        self.budget_id = budget_id
        self.requested_amount = requested_amount
        self.available_balance = available_balance
        self.budget_coding = budget_coding
        
        message = (
            f"Insufficient funds for budget {budget_coding or budget_id}: "
            f"requested {requested_amount:,} Rials, "
            f"available {available_balance:,} Rials"
        )
        super().__init__(message)


class InvalidOperationError(Exception):
    """
    Raised when an operation is logically invalid.
    
    Examples:
    - Trying to release more than blocked
    - Trying to spend more than blocked
    - Operating on non-existent budget row
    """
    def __init__(self, message: str, budget_id: Optional[int] = None):
        self.budget_id = budget_id
        super().__init__(message)


# ============================================
# Helper Functions
# ============================================

def _get_budget_row_for_update(db: Session, budget_id: int) -> BudgetRow:
    """
    Fetch a budget row with row-level locking (SELECT FOR UPDATE).
    
    This prevents other transactions from modifying this row until
    the current transaction is committed or rolled back.
    """
    stmt = (
        select(BudgetRow)
        .where(BudgetRow.id == budget_id)
        .with_for_update()  # Row-level lock
    )
    result = db.execute(stmt)
    budget_row = result.scalar_one_or_none()
    
    if budget_row is None:
        raise InvalidOperationError(
            f"Budget row with ID {budget_id} not found",
            budget_id=budget_id
        )
    
    return budget_row


def _create_transaction(
    db: Session,
    budget_row: BudgetRow,
    amount: int,
    operation_type: OperationType,
    user_id: str,
    reference_doc: Optional[str],
    notes: Optional[str],
    balance_before: int,
    balance_after: int
) -> BudgetTransaction:
    """Create an audit trail entry for a budget operation."""
    transaction = BudgetTransaction(
        budget_row_id=budget_row.id,
        amount=amount,
        operation_type=operation_type,
        reference_doc=reference_doc,
        performed_by=user_id,
        notes=notes,
        balance_before=balance_before,
        balance_after=balance_after,
        created_at=datetime.utcnow()
    )
    db.add(transaction)
    return transaction


# ============================================
# Atomic Budget Operations
# ============================================

def block_funds(
    db: Session,
    budget_id: int,
    amount: int,
    user_id: str,
    reference_doc: Optional[str] = None,
    notes: Optional[str] = None
) -> BudgetTransaction:
    """
    Atomically block funds for a pending request.
    
    This operation:
    1. Acquires a row-level lock on the budget row
    2. Checks if sufficient balance is available
    3. Increases blocked_amount
    4. Creates an audit trail entry
    
    Args:
        db: Database session (should be in a transaction)
        budget_id: ID of the BudgetRow to operate on
        amount: Amount to block (in Rials, must be positive)
        user_id: ID of the user performing this operation
        reference_doc: Optional reference (e.g., "Request-1024")
        notes: Optional notes for the audit trail
    
    Returns:
        BudgetTransaction: The created audit trail entry
    
    Raises:
        InsufficientFundsError: If available balance < amount
        InvalidOperationError: If budget row not found or amount invalid
    """
    if amount <= 0:
        raise InvalidOperationError(
            f"Block amount must be positive, got {amount}",
            budget_id=budget_id
        )
    
    # Lock the row
    budget_row = _get_budget_row_for_update(db, budget_id)
    
    # Calculate available balance
    balance_before = budget_row.remaining_balance
    
    # Check if we have sufficient funds
    if balance_before < amount:
        raise InsufficientFundsError(
            budget_id=budget_id,
            requested_amount=amount,
            available_balance=balance_before,
            budget_coding=budget_row.budget_coding
        )
    
    # Update the budget row
    budget_row.blocked_amount += amount
    budget_row.updated_at = datetime.utcnow()
    
    # Calculate new balance
    balance_after = budget_row.remaining_balance
    
    # Create audit trail
    transaction = _create_transaction(
        db=db,
        budget_row=budget_row,
        amount=amount,
        operation_type=OperationType.BLOCK,
        user_id=user_id,
        reference_doc=reference_doc,
        notes=notes,
        balance_before=balance_before,
        balance_after=balance_after
    )
    
    db.flush()  # Ensure DB constraint is checked
    
    return transaction


def release_funds(
    db: Session,
    budget_id: int,
    amount: int,
    user_id: str,
    reference_doc: Optional[str] = None,
    notes: Optional[str] = None
) -> BudgetTransaction:
    """
    Release blocked funds when a request is rejected.
    
    This operation:
    1. Acquires a row-level lock on the budget row
    2. Decreases blocked_amount
    3. Creates an audit trail entry
    
    Args:
        db: Database session (should be in a transaction)
        budget_id: ID of the BudgetRow to operate on
        amount: Amount to release (in Rials, must be positive)
        user_id: ID of the user performing this operation
        reference_doc: Optional reference (e.g., "Request-1024")
        notes: Optional notes (e.g., rejection reason)
    
    Returns:
        BudgetTransaction: The created audit trail entry
    
    Raises:
        InvalidOperationError: If amount > blocked_amount or other issues
    """
    if amount <= 0:
        raise InvalidOperationError(
            f"Release amount must be positive, got {amount}",
            budget_id=budget_id
        )
    
    # Lock the row
    budget_row = _get_budget_row_for_update(db, budget_id)
    
    # Validate operation
    if amount > budget_row.blocked_amount:
        raise InvalidOperationError(
            f"Cannot release {amount:,} Rials: only {budget_row.blocked_amount:,} blocked",
            budget_id=budget_id
        )
    
    balance_before = budget_row.remaining_balance
    
    # Update the budget row
    budget_row.blocked_amount -= amount
    budget_row.updated_at = datetime.utcnow()
    
    balance_after = budget_row.remaining_balance
    
    # Create audit trail
    transaction = _create_transaction(
        db=db,
        budget_row=budget_row,
        amount=amount,
        operation_type=OperationType.RELEASE,
        user_id=user_id,
        reference_doc=reference_doc,
        notes=notes,
        balance_before=balance_before,
        balance_after=balance_after
    )
    
    db.flush()
    
    return transaction


def confirm_spend(
    db: Session,
    budget_id: int,
    amount: int,
    user_id: str,
    reference_doc: Optional[str] = None,
    notes: Optional[str] = None
) -> BudgetTransaction:
    """
    Confirm a payment: move funds from blocked to spent.
    
    This operation:
    1. Acquires a row-level lock on the budget row
    2. Decreases blocked_amount
    3. Increases spent_amount
    4. Creates an audit trail entry
    
    Use this when a payment is approved and the check is signed.
    
    Args:
        db: Database session (should be in a transaction)
        budget_id: ID of the BudgetRow to operate on
        amount: Amount being spent (in Rials, must be positive)
        user_id: ID of the user performing this operation
        reference_doc: Optional reference (e.g., "Request-1024", "Check-5678")
        notes: Optional notes for the audit trail
    
    Returns:
        BudgetTransaction: The created audit trail entry
    
    Raises:
        InvalidOperationError: If amount > blocked_amount or other issues
    """
    if amount <= 0:
        raise InvalidOperationError(
            f"Spend amount must be positive, got {amount}",
            budget_id=budget_id
        )
    
    # Lock the row
    budget_row = _get_budget_row_for_update(db, budget_id)
    
    # Validate operation
    if amount > budget_row.blocked_amount:
        raise InvalidOperationError(
            f"Cannot spend {amount:,} Rials: only {budget_row.blocked_amount:,} blocked. "
            f"Funds must be blocked before they can be spent.",
            budget_id=budget_id
        )
    
    balance_before = budget_row.remaining_balance
    
    # Update the budget row (blocked → spent)
    budget_row.blocked_amount -= amount
    budget_row.spent_amount += amount
    budget_row.updated_at = datetime.utcnow()
    
    balance_after = budget_row.remaining_balance
    
    # Create audit trail
    transaction = _create_transaction(
        db=db,
        budget_row=budget_row,
        amount=amount,
        operation_type=OperationType.SPEND,
        user_id=user_id,
        reference_doc=reference_doc,
        notes=notes,
        balance_before=balance_before,
        balance_after=balance_after
    )
    
    db.flush()
    
    return transaction


def increase_budget(
    db: Session,
    budget_id: int,
    amount: int,
    user_id: str,
    reference_doc: Optional[str] = None,
    notes: Optional[str] = None
) -> BudgetTransaction:
    """
    Increase the approved budget (budget amendment).
    
    This is an administrative operation for budget amendments.
    
    Args:
        db: Database session
        budget_id: ID of the BudgetRow to operate on
        amount: Amount to add to approved_amount (must be positive)
        user_id: ID of the admin performing this operation
        reference_doc: Reference to the amendment document
        notes: Optional notes
    
    Returns:
        BudgetTransaction: The created audit trail entry
    """
    if amount <= 0:
        raise InvalidOperationError(
            f"Budget increase amount must be positive, got {amount}",
            budget_id=budget_id
        )
    
    # Lock the row
    budget_row = _get_budget_row_for_update(db, budget_id)
    
    balance_before = budget_row.remaining_balance
    
    # Increase approved amount
    budget_row.approved_amount += amount
    budget_row.updated_at = datetime.utcnow()
    
    balance_after = budget_row.remaining_balance
    
    # Create audit trail
    transaction = _create_transaction(
        db=db,
        budget_row=budget_row,
        amount=amount,
        operation_type=OperationType.INCREASE_BUDGET,
        user_id=user_id,
        reference_doc=reference_doc,
        notes=notes,
        balance_before=balance_before,
        balance_after=balance_after
    )
    
    db.flush()
    
    return transaction


# ============================================
# Query Functions
# ============================================

def get_budget_status(db: Session, budget_id: int) -> dict:
    """
    Get the current status of a budget row.
    
    Returns:
        dict with approved, blocked, spent, remaining amounts
    """
    budget_row = db.query(BudgetRow).filter(BudgetRow.id == budget_id).first()
    
    if budget_row is None:
        raise InvalidOperationError(f"Budget row {budget_id} not found")
    
    return {
        "id": budget_row.id,
        "budget_coding": budget_row.budget_coding,
        "description": budget_row.description,
        "approved_amount": budget_row.approved_amount,
        "blocked_amount": budget_row.blocked_amount,
        "spent_amount": budget_row.spent_amount,
        "remaining_balance": budget_row.remaining_balance,
        "fiscal_year": budget_row.fiscal_year,
        "utilization_rate": (
            (budget_row.spent_amount + budget_row.blocked_amount) / budget_row.approved_amount * 100
            if budget_row.approved_amount > 0 else 0
        )
    }


def get_transaction_history(
    db: Session,
    budget_id: int,
    limit: int = 100
) -> list[BudgetTransaction]:
    """
    Get transaction history for a budget row.
    
    Returns:
        List of BudgetTransaction records, most recent first
    """
    return (
        db.query(BudgetTransaction)
        .filter(BudgetTransaction.budget_row_id == budget_id)
        .order_by(BudgetTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
