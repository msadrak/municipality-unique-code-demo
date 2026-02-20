"""
Contract Lifecycle Service - Sprint 2
=======================================

Business logic for contract creation, state transitions, and template rendering.

Integrates with:
- budget_service: block/release for budget reservation lifecycle
- CreditSystemPort (ACL): reserve funds in external credit system (mock)
- BudgetRow, Contract, Contractor, ContractTemplate models

Key Design Decisions:
- Contract number format: CTR-{fiscal_year}-{NNNN} (sequential, zero-padded)
- State machine enforced at service layer (not DB constraints)
- Budget reservation happens at draft creation and remains blocked until execution
- Rejected contracts release reserved budget
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.models import (
    Contract, ContractStatus,
    Contractor, ContractTemplate, BudgetRow,
)
from app.services.budget_service import block_funds, release_funds
from app.integrations import get_credit_port
from app.integrations.ports import CreditSubmitRequest


# ============================================
# State Machine
# ============================================

VALID_TRANSITIONS: dict[str, list[str]] = {
    ContractStatus.DRAFT.value: [ContractStatus.PENDING_APPROVAL.value],
    ContractStatus.PENDING_APPROVAL.value: [
        ContractStatus.APPROVED.value,
        ContractStatus.REJECTED.value,
    ],
    ContractStatus.APPROVED.value: [ContractStatus.NOTIFIED.value],
    ContractStatus.REJECTED.value: [ContractStatus.DRAFT.value],
    ContractStatus.NOTIFIED.value: [ContractStatus.IN_PROGRESS.value],
    ContractStatus.IN_PROGRESS.value: [ContractStatus.PENDING_COMPLETION.value],
    ContractStatus.PENDING_COMPLETION.value: [ContractStatus.COMPLETED.value],
    ContractStatus.COMPLETED.value: [ContractStatus.GUARANTEE_PERIOD.value],
    ContractStatus.GUARANTEE_PERIOD.value: [ContractStatus.CLOSED.value],
}


# ============================================
# Custom Exceptions
# ============================================

class ContractNotFoundError(Exception):
    """Raised when a contract is not found."""
    def __init__(self, contract_id: int):
        self.contract_id = contract_id
        super().__init__(f"قرارداد با شناسه {contract_id} یافت نشد")


class InvalidTransitionError(Exception):
    """Raised for invalid state transitions."""
    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(
            f"انتقال وضعیت از {current_status} به {new_status} مجاز نیست"
        )


class ContractValidationError(Exception):
    """Raised for domain validation errors during creation."""
    def __init__(self, message: str):
        super().__init__(message)


# ============================================
# Contract Number Generation
# ============================================

def _generate_contract_number(db: Session, fiscal_year: str = "1403") -> str:
    """
    Generate a unique contract number: CTR-{fiscal_year}-{NNNN}
    
    Sequence is based on the count of existing contracts in the same fiscal year.
    Thread-safe: unique constraint on contract_number column handles race conditions.
    """
    count = db.query(func.count(Contract.id)).filter(
        Contract.contract_number.like(f"CTR-{fiscal_year}-%")
    ).scalar() or 0

    sequence = count + 1
    return f"CTR-{fiscal_year}-{sequence:04d}"


# ============================================
# Draft Creation
# ============================================

def create_draft(
    db: Session,
    budget_row_id: int,
    contractor_id: int,
    template_id: int,
    title: str,
    total_amount: int,
    user_id: int,
    template_data: Optional[Dict[str, Any]] = None,
    start_date=None,
    end_date=None,
    fiscal_year: str = "1403",
) -> Contract:
    """
    Create a contract draft with budget reservation.
    
    Steps:
    1. Validate references (budget_row, contractor, template)
    2. Check budget has enough remaining credit
    3. Reserve funds via CreditSystemPort (ACL mock)
    4. Block funds in BudgetRow
    5. Generate unique contract_number
    6. Create Contract record with status DRAFT
    
    Raises:
        ContractValidationError: if references invalid or insufficient funds
    """
    # --- (1) Validate references ---
    budget_row = db.query(BudgetRow).filter(BudgetRow.id == budget_row_id).first()
    if not budget_row:
        raise ContractValidationError(f"ردیف بودجه با شناسه {budget_row_id} یافت نشد")

    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    if not contractor:
        raise ContractValidationError(f"پیمانکار با شناسه {contractor_id} یافت نشد")

    template = db.query(ContractTemplate).filter(ContractTemplate.id == template_id).first()
    if not template:
        raise ContractValidationError(f"قالب قرارداد با شناسه {template_id} یافت نشد")

    # --- (2) Budget credit check ---
    if budget_row.remaining_balance < total_amount:
        raise ContractValidationError(
            f"اعتبار ردیف بودجه کافی نیست. "
            f"مانده: {budget_row.remaining_balance:,} ریال، "
            f"درخواست: {total_amount:,} ریال"
        )

    # --- (3) Reserve via CreditSystemPort (ACL) ---
    credit_port = get_credit_port()
    credit_response = credit_port.submit_credit_request(
        CreditSubmitRequest(
            budget_code=budget_row.budget_coding,
            amount=float(total_amount),
            description=f"رزرو بودجه برای قرارداد: {title}",
            zone_id=budget_row.org_unit_id or 0,
            fiscal_year=fiscal_year,
        )
    )

    # --- (4) Block funds in BudgetRow ---
    block_funds(
        db=db,
        budget_id=budget_row_id,
        amount=total_amount,
        user_id=str(user_id),
        reference_doc=f"Contract-Draft",
        notes=f"رزرو بودجه برای قرارداد: {title}",
    )

    # --- (5) Generate contract number ---
    contract_number = _generate_contract_number(db, fiscal_year)

    # --- (6) Create Contract record ---
    contract = Contract(
        contract_number=contract_number,
        title=title,
        contractor_id=contractor_id,
        template_id=template_id,
        budget_row_id=budget_row_id,
        org_unit_id=budget_row.org_unit_id,
        status=ContractStatus.DRAFT,
        total_amount=total_amount,
        template_data=template_data,
        start_date=start_date,
        end_date=end_date,
        created_by_id=user_id,
        metadata_extra={
            "credit_ref_id": credit_response.ref_id,
            "credit_status": credit_response.status,
        },
    )
    db.add(contract)
    db.flush()

    return contract


# ============================================
# State Transitions
# ============================================

def transition_status(
    db: Session,
    contract_id: int,
    new_status: str,
    user_id: int,
) -> Contract:
    """
    Transition a contract to a new status with business rule enforcement.
    
    Side effects:
    - APPROVED: no budget movement (funds stay blocked for statement-based execution)
    - REJECTED: release_funds to free the reserved budget
    
    Raises:
        ContractNotFoundError: if contract not found
        InvalidTransitionError: if transition is not allowed
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise ContractNotFoundError(contract_id)

    current = contract.status.value if isinstance(contract.status, ContractStatus) else contract.status
    allowed = VALID_TRANSITIONS.get(current, [])

    if new_status not in allowed:
        raise InvalidTransitionError(current, new_status)

    # --- Side effects ---
    if new_status == ContractStatus.REJECTED.value and contract.budget_row_id:
        # Release the reservation
        release_funds(
            db=db,
            budget_id=contract.budget_row_id,
            amount=contract.total_amount,
            user_id=str(user_id),
            reference_doc=f"Contract-{contract.contract_number}",
            notes=f"رد قرارداد {contract.contract_number} - آزادسازی بودجه",
        )

    # --- Update status ---
    contract.status = ContractStatus(new_status)
    contract.updated_at = datetime.utcnow()
    contract.version = (contract.version or 1) + 1

    db.flush()
    return contract


# ============================================
# Template Rendering
# ============================================

def render_contract(db: Session, contract_id: int) -> dict:
    """
    Merge template JSON Schema with contract's current data.
    
    Returns a dict containing:
    - schema_definition: the JSON Schema from the template
    - default_values: template defaults
    - current_data: data already filled on this contract
    
    Raises:
        ContractNotFoundError: if contract not found
        ContractValidationError: if template missing
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise ContractNotFoundError(contract_id)

    template = db.query(ContractTemplate).filter(
        ContractTemplate.id == contract.template_id
    ).first()
    if not template:
        raise ContractValidationError(
            f"قالب قرارداد با شناسه {contract.template_id} یافت نشد"
        )

    return {
        "contract_id": contract.id,
        "contract_number": contract.contract_number,
        "status": contract.status.value if isinstance(contract.status, ContractStatus) else contract.status,
        "template_id": template.id,
        "template_code": template.code,
        "template_title": template.title,
        "schema_definition": template.schema_definition or {},
        "default_values": template.default_values,
        "current_data": contract.template_data,
    }
