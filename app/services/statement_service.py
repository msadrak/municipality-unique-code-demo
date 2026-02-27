"""
Progress Statement Service - 4-Stage Approval Workflow
======================================================

Business rules:
- Statements can only be created for APPROVED / IN_PROGRESS contracts
- Over-payment prevention is enforced at creation time
- State machine: DRAFT → PENDING_L1 → PENDING_L2 → PENDING_L3 → PENDING_L4 → APPROVED
- At any stage → REJECTED (with reason)
- On APPROVED: a linked Transaction should be created/advanced for payment processing
"""

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Contract,
    ContractStatus,
    ProgressStatement,
    ProgressStatementStatus,
)
from app.services.budget_service import confirm_spend


# ============================================================
# State Machine — 4-Stage Approval Workflow
# ============================================================

VALID_TRANSITIONS: dict[str, list[str]] = {
    ProgressStatementStatus.DRAFT.value: [ProgressStatementStatus.PENDING_L1.value],
    ProgressStatementStatus.PENDING_L1.value: [
        ProgressStatementStatus.PENDING_L2.value,
        ProgressStatementStatus.REJECTED.value,
    ],
    ProgressStatementStatus.PENDING_L2.value: [
        ProgressStatementStatus.PENDING_L3.value,
        ProgressStatementStatus.REJECTED.value,
    ],
    ProgressStatementStatus.PENDING_L3.value: [
        ProgressStatementStatus.PENDING_L4.value,
        ProgressStatementStatus.REJECTED.value,
    ],
    ProgressStatementStatus.PENDING_L4.value: [
        ProgressStatementStatus.APPROVED.value,
        ProgressStatementStatus.REJECTED.value,
    ],
    # APPROVED and REJECTED are terminal states for ProgressStatement.
    # Payment is handled at the Transaction level.
}

# Maps status to approval level for current_approval_level tracking
STATUS_TO_LEVEL: dict[str, int] = {
    ProgressStatementStatus.DRAFT.value: 0,
    ProgressStatementStatus.PENDING_L1.value: 1,
    ProgressStatementStatus.PENDING_L2.value: 2,
    ProgressStatementStatus.PENDING_L3.value: 3,
    ProgressStatementStatus.PENDING_L4.value: 4,
    ProgressStatementStatus.APPROVED.value: 4,
    ProgressStatementStatus.REJECTED.value: 0,
}


# ============================================================
# Custom Exceptions
# ============================================================

class StatementNotFoundError(Exception):
    """Raised when a progress statement is not found."""

    def __init__(self, statement_id: int):
        self.statement_id = statement_id
        super().__init__(f"Statement with ID {statement_id} was not found")


class StatementValidationError(Exception):
    """Raised for domain validation errors."""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidStatementTransitionError(Exception):
    """Raised for invalid state transitions."""

    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(
            f"Invalid statement transition from {current_status} to {new_status}"
        )


class OverPaymentError(Exception):
    """Raised when a statement would exceed the contract total amount."""

    def __init__(
        self,
        contract_total: int,
        already_committed: int,
        requested: int,
    ):
        self.contract_total = contract_total
        self.already_committed = already_committed
        self.requested = requested
        self.available = contract_total - already_committed
        super().__init__(
            "Statement amount exceeds contract ceiling. "
            f"contract_total={contract_total:,}, "
            f"already_committed={already_committed:,}, "
            f"requested={requested:,}, "
            f"available={self.available:,}"
        )


# ============================================================
# Internal Helpers
# ============================================================

def _status_value(raw_status) -> str:
    return raw_status.value if hasattr(raw_status, "value") else str(raw_status)


def _generate_statement_number(contract: Contract, sequence: int) -> str:
    """Generate statement number: PS-{contract_number}-{NN}."""
    return f"PS-{contract.contract_number}-{sequence:02d}"


def _get_contract_for_update(db: Session, contract_id: int) -> Optional[Contract]:
    """
    Fetch contract row with a lock for race-safe financial checks.
    On SQLite this is effectively a no-op but remains correct for PostgreSQL.
    """
    return (
        db.query(Contract)
        .filter(Contract.id == contract_id)
        .with_for_update()
        .first()
    )


def _get_committed_amount(db: Session, contract_id: int) -> int:
    """
    Sum of net_amount for all statements linked to this contract.
    Any existing statement counts toward ceiling protection.
    """
    result = (
        db.query(func.coalesce(func.sum(ProgressStatement.net_amount), 0))
        .filter(ProgressStatement.contract_id == contract_id)
        .scalar()
    )
    return int(result or 0)


def _resolve_financial_amounts(
    *,
    amount: Optional[int],
    gross_amount: Optional[int],
    deductions: int,
) -> tuple[int, int]:
    """
    Resolve gross/net values from request variants.

    Supported payload styles:
    - Preferred: amount (net), optional gross/deductions
    - Backward compatible: gross_amount + deductions
    """
    if deductions < 0:
        raise StatementValidationError("deductions cannot be negative")

    if amount is None and gross_amount is None:
        raise StatementValidationError("Either amount or gross_amount is required")

    if amount is not None and amount <= 0:
        raise StatementValidationError("amount must be positive")

    if gross_amount is not None and gross_amount <= 0:
        raise StatementValidationError("gross_amount must be positive")

    if gross_amount is None and amount is not None:
        gross_amount = amount + deductions
        net_amount = amount
    else:
        assert gross_amount is not None  # guarded above
        net_amount = gross_amount - deductions
        if net_amount <= 0:
            raise StatementValidationError("net amount must be positive")

        # If caller provided both styles, enforce consistency.
        if amount is not None and amount != net_amount:
            raise StatementValidationError(
                "Inconsistent payload: amount must equal gross_amount - deductions"
            )

    return gross_amount, net_amount


# ============================================================
# Statement Creation
# ============================================================

def create_statement(
    db: Session,
    contract_id: int,
    description: str,
    user_id: int,
    amount: Optional[int] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    statement_type: str = "INTERIM",
    gross_amount: Optional[int] = None,
    deductions: int = 0,
    originating_organ: Optional[str] = None,
    template_data: Optional[dict] = None,
    insurance_deduction: int = 0,
    tax_deduction: int = 0,
    advance_payment_amount: int = 0,
    other_deductions: int = 0,
) -> ProgressStatement:
    """
    Create a progress statement draft with over-payment prevention.

    Validations:
    1) Contract must exist and be APPROVED / IN_PROGRESS.
    2) sum(previous_statements) + new_amount <= contract.total_amount.
    """
    if not description or not description.strip():
        raise StatementValidationError("description is required")

    if period_start and period_end and period_start > period_end:
        raise StatementValidationError("period_start cannot be after period_end")

    contract = _get_contract_for_update(db, contract_id)
    if not contract:
        raise StatementValidationError(f"Contract with ID {contract_id} was not found")

    contract_status = _status_value(contract.status)
    if contract_status not in {
        ContractStatus.APPROVED.value,
        ContractStatus.IN_PROGRESS.value,
    }:
        raise StatementValidationError(
            "Statements can only be created for APPROVED or IN_PROGRESS contracts. "
            f"Current status: {contract_status}"
        )

    resolved_gross, resolved_net = _resolve_financial_amounts(
        amount=amount,
        gross_amount=gross_amount,
        deductions=deductions,
    )

    committed = _get_committed_amount(db, contract_id)
    if committed + resolved_net > contract.total_amount:
        raise OverPaymentError(
            contract_total=contract.total_amount,
            already_committed=committed,
            requested=resolved_net,
        )

    existing_count = (
        db.query(func.count(ProgressStatement.id))
        .filter(ProgressStatement.contract_id == contract_id)
        .scalar()
    ) or 0
    sequence = existing_count + 1
    statement_number = _generate_statement_number(contract, sequence)

    statement = ProgressStatement(
        statement_number=statement_number,
        contract_id=contract_id,
        sequence_number=sequence,
        statement_type=statement_type,
        description=description.strip(),
        period_start=period_start,
        period_end=period_end,
        originating_organ=originating_organ,
        template_data=template_data,
        gross_amount=resolved_gross,
        deductions=deductions,
        net_amount=resolved_net,
        cumulative_amount=committed + resolved_net,
        insurance_deduction=insurance_deduction,
        tax_deduction=tax_deduction,
        advance_payment_amount=advance_payment_amount,
        other_deductions=other_deductions,
        status=ProgressStatementStatus.DRAFT,
        current_approval_level=0,
        submitted_by_id=user_id,
    )
    db.add(statement)
    db.flush()
    return statement


# ============================================================
# State Transitions
# ============================================================

def submit_statement(db: Session, statement_id: int, user_id: int) -> ProgressStatement:
    """Transition DRAFT → PENDING_L1 (submit for review)."""
    return _transition(db, statement_id, ProgressStatementStatus.PENDING_L1.value, user_id)


def approve_l1(db: Session, statement_id: int, user_id: int, review_comment: Optional[str] = None) -> ProgressStatement:
    """Transition PENDING_L1 → PENDING_L2 (section/technical review passed)."""
    statement = _transition(db, statement_id, ProgressStatementStatus.PENDING_L2.value, user_id)
    statement.reviewed_by_id = user_id
    statement.reviewed_at = datetime.utcnow()
    statement.review_comment = review_comment
    db.flush()
    return statement


def approve_l2(db: Session, statement_id: int, user_id: int, review_comment: Optional[str] = None) -> ProgressStatement:
    """Transition PENDING_L2 → PENDING_L3 (department head approved)."""
    statement = _transition(db, statement_id, ProgressStatementStatus.PENDING_L3.value, user_id)
    statement.reviewed_by_id = user_id
    statement.reviewed_at = datetime.utcnow()
    statement.review_comment = review_comment
    db.flush()
    return statement


def approve_l3(db: Session, statement_id: int, user_id: int, review_comment: Optional[str] = None) -> ProgressStatement:
    """Transition PENDING_L3 → PENDING_L4 (zone/manager approved)."""
    statement = _transition(db, statement_id, ProgressStatementStatus.PENDING_L4.value, user_id)
    statement.reviewed_by_id = user_id
    statement.reviewed_at = datetime.utcnow()
    statement.review_comment = review_comment
    db.flush()
    return statement


def approve_l4(db: Session, statement_id: int, user_id: int, review_comment: Optional[str] = None) -> ProgressStatement:
    """Transition PENDING_L4 → APPROVED (finance/treasury final approval)."""
    statement = _transition(db, statement_id, ProgressStatementStatus.APPROVED.value, user_id)
    statement.reviewed_by_id = user_id
    statement.reviewed_at = datetime.utcnow()
    statement.review_comment = review_comment
    db.flush()
    return statement


def reject_statement(
    db: Session,
    statement_id: int,
    user_id: int,
    rejection_reason: Optional[str] = None,
) -> ProgressStatement:
    """
    Reject a statement at any pending stage → REJECTED.
    
    Rejection is allowed from PENDING_L1, PENDING_L2, PENDING_L3, PENDING_L4.
    """
    statement = (
        db.query(ProgressStatement)
        .filter(ProgressStatement.id == statement_id)
        .with_for_update()
        .first()
    )
    if not statement:
        raise StatementNotFoundError(statement_id)

    current = _status_value(statement.status)
    allowed = VALID_TRANSITIONS.get(current, [])
    if ProgressStatementStatus.REJECTED.value not in allowed:
        raise InvalidStatementTransitionError(current, ProgressStatementStatus.REJECTED.value)

    statement.status = ProgressStatementStatus.REJECTED
    statement.rejected_by_id = user_id
    statement.rejected_at = datetime.utcnow()
    statement.rejection_reason = rejection_reason
    statement.current_approval_level = 0
    statement.updated_at = datetime.utcnow()
    statement.version = (statement.version or 1) + 1

    db.flush()
    return statement


# Legacy compatibility alias
def approve_statement(
    db: Session,
    statement_id: int,
    user_id: int,
    review_comment: Optional[str] = None,
) -> ProgressStatement:
    """
    Legacy approve function — advances statement to next approval level.
    
    Determines the correct transition based on current status.
    """
    statement = (
        db.query(ProgressStatement)
        .filter(ProgressStatement.id == statement_id)
        .with_for_update()
        .first()
    )
    if not statement:
        raise StatementNotFoundError(statement_id)

    current = _status_value(statement.status)
    
    # Route to appropriate level-specific approve function
    level_map = {
        ProgressStatementStatus.PENDING_L1.value: approve_l1,
        ProgressStatementStatus.PENDING_L2.value: approve_l2,
        ProgressStatementStatus.PENDING_L3.value: approve_l3,
        ProgressStatementStatus.PENDING_L4.value: approve_l4,
    }
    
    approve_fn = level_map.get(current)
    if not approve_fn:
        # Find the first non-REJECTED transition
        allowed = VALID_TRANSITIONS.get(current, [])
        non_reject = [s for s in allowed if s != ProgressStatementStatus.REJECTED.value]
        if not non_reject:
            raise InvalidStatementTransitionError(current, "APPROVED")
        raise InvalidStatementTransitionError(current, non_reject[0])
    
    return approve_fn(db, statement_id, user_id, review_comment)


def _transition(
    db: Session,
    statement_id: int,
    new_status: str,
    user_id: int,
) -> ProgressStatement:
    """Generic state transition with validation."""
    statement = (
        db.query(ProgressStatement)
        .filter(ProgressStatement.id == statement_id)
        .with_for_update()
        .first()
    )
    if not statement:
        raise StatementNotFoundError(statement_id)

    current = _status_value(statement.status)
    allowed = VALID_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise InvalidStatementTransitionError(current, new_status)

    statement.status = ProgressStatementStatus(new_status)
    statement.current_approval_level = STATUS_TO_LEVEL.get(new_status, 0)
    statement.updated_at = datetime.utcnow()
    statement.version = (statement.version or 1) + 1

    if new_status == ProgressStatementStatus.PENDING_L1.value:
        statement.submitted_at = datetime.utcnow()

    db.flush()
    return statement


# ============================================================
# Query Functions
# ============================================================

def get_contract_statements(db: Session, contract_id: int) -> List[ProgressStatement]:
    """Get all statements for a contract, ordered by sequence."""
    return (
        db.query(ProgressStatement)
        .filter(ProgressStatement.contract_id == contract_id)
        .order_by(ProgressStatement.sequence_number.asc())
        .all()
    )


def get_statement_financial_summary(db: Session, contract_id: int) -> dict:
    """Get financial summary for a contract's statements."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise StatementValidationError(f"Contract with ID {contract_id} was not found")

    statements = get_contract_statements(db, contract_id)
    total_gross = sum(s.gross_amount for s in statements)
    total_deductions = sum(s.deductions for s in statements)
    total_net = sum(s.net_amount for s in statements)
    total_approved = sum(
        s.net_amount
        for s in statements
        if _status_value(s.status) == ProgressStatementStatus.APPROVED.value
    )

    return {
        "contract_id": contract_id,
        "contract_total": contract.total_amount,
        "statement_count": len(statements),
        "total_gross": total_gross,
        "total_deductions": total_deductions,
        "total_net_committed": total_net,
        "total_approved": total_approved,
        "remaining": contract.total_amount - total_net,
    }
