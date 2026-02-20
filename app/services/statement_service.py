"""
Progress Statement Service - Sprint 3
====================================

Business rules:
- Statements can only be created for APPROVED / IN_PROGRESS contracts
- Over-payment prevention is enforced at creation time
- State machine: DRAFT -> SUBMITTED -> APPROVED -> PAID
- On PAID: blocked budget is converted to spent budget (real execution)
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
# State Machine
# ============================================================

VALID_TRANSITIONS: dict[str, list[str]] = {
    ProgressStatementStatus.DRAFT.value: [ProgressStatementStatus.SUBMITTED.value],
    ProgressStatementStatus.SUBMITTED.value: [ProgressStatementStatus.APPROVED.value],
    ProgressStatementStatus.APPROVED.value: [ProgressStatementStatus.PAID.value],
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
    - Sprint 3 preferred: amount (net), optional gross/deductions
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
        gross_amount=resolved_gross,
        deductions=deductions,
        net_amount=resolved_net,
        cumulative_amount=committed + resolved_net,
        status=ProgressStatementStatus.DRAFT,
        submitted_by_id=user_id,
    )
    db.add(statement)
    db.flush()
    return statement


# ============================================================
# State Transitions
# ============================================================

def submit_statement(db: Session, statement_id: int, user_id: int) -> ProgressStatement:
    """Transition DRAFT -> SUBMITTED."""
    return _transition(db, statement_id, ProgressStatementStatus.SUBMITTED.value, user_id)


def approve_statement(
    db: Session,
    statement_id: int,
    user_id: int,
    review_comment: Optional[str] = None,
) -> ProgressStatement:
    """Transition SUBMITTED -> APPROVED."""
    statement = _transition(db, statement_id, ProgressStatementStatus.APPROVED.value, user_id)
    statement.reviewed_by_id = user_id
    statement.reviewed_at = datetime.utcnow()
    statement.review_comment = review_comment
    db.flush()
    return statement


def pay_statement(db: Session, statement_id: int, user_id: int) -> ProgressStatement:
    """
    Transition APPROVED -> PAID and execute budget movement blocked -> spent.
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
    if current != ProgressStatementStatus.APPROVED.value:
        raise InvalidStatementTransitionError(
            current,
            ProgressStatementStatus.PAID.value,
        )

    contract = _get_contract_for_update(db, statement.contract_id)
    if not contract:
        raise StatementValidationError(
            f"Contract with ID {statement.contract_id} was not found"
        )

    contract_status = _status_value(contract.status)
    if contract_status not in {
        ContractStatus.APPROVED.value,
        ContractStatus.IN_PROGRESS.value,
    }:
        raise StatementValidationError(
            "Payment is only allowed when contract is APPROVED or IN_PROGRESS. "
            f"Current status: {contract_status}"
        )

    projected_paid = (contract.paid_amount or 0) + statement.net_amount
    if projected_paid > contract.total_amount:
        raise OverPaymentError(
            contract_total=contract.total_amount,
            already_committed=contract.paid_amount or 0,
            requested=statement.net_amount,
        )

    if not contract.budget_row_id:
        raise StatementValidationError(
            "Contract is missing budget_row_id and cannot execute payment"
        )

    confirm_spend(
        db=db,
        budget_id=contract.budget_row_id,
        amount=statement.net_amount,
        user_id=str(user_id),
        reference_doc=f"Statement-{statement.statement_number}",
        notes=f"Statement payment for contract {contract.contract_number}",
    )

    contract.paid_amount = projected_paid
    contract.updated_at = datetime.utcnow()

    statement.status = ProgressStatementStatus.PAID
    statement.updated_at = datetime.utcnow()
    statement.version = (statement.version or 1) + 1

    db.flush()
    return statement


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
    statement.updated_at = datetime.utcnow()
    statement.version = (statement.version or 1) + 1

    if new_status == ProgressStatementStatus.SUBMITTED.value:
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
    total_paid = sum(
        s.net_amount
        for s in statements
        if _status_value(s.status) == ProgressStatementStatus.PAID.value
    )

    return {
        "contract_id": contract_id,
        "contract_total": contract.total_amount,
        "statement_count": len(statements),
        "total_gross": total_gross,
        "total_deductions": total_deductions,
        "total_net_committed": total_net,
        "total_paid": total_paid,
        "remaining": contract.total_amount - total_net,
    }
