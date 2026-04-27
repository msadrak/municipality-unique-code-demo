from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from decimal import Decimal

import jdatetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.database import get_db
from app.models import (
    Activity,
    ContractorStatement,
    RegionalAttendanceSheet,
    Transaction,
    TransactionAllocation,
    User,
    WorkPeriod,
)
from app.models.enums import WorkFlowStatus
from app.schemas.hr_finance import (
    GeneratedHRTransactionCodeOut,
    HRFinanceFinalizeRequest,
    HRFinanceWorkflowContextOut,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hr-finance", tags=["hr-finance"])

FINAL_TRANSACTION_STATUS = "SENT_TO_FINANCE"
ALLOWED_FINALIZE_STATUSES = {"DRAFT", "PENDING_UNIQUE_CODE"}


def _extract_work_period_id(transaction: Transaction) -> int | None:
    form_data = transaction.form_data if isinstance(transaction.form_data, dict) else {}
    raw_value = form_data.get("attendance_work_period_id", form_data.get("work_period_id"))
    if raw_value is None:
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _build_work_period_date_range(year: int, month: int) -> dict[str, str]:
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid work period month '{month}' on persisted transaction context.",
        )

    start_date = jdatetime.date(year, month, 1)
    end_day = 31 if month <= 6 else 30
    if month == 12:
        try:
            jdatetime.date(year, month, 30)
        except ValueError:
            end_day = 29

    end_date = jdatetime.date(year, month, end_day)
    return {
        "start": start_date.strftime("%Y/%m/%d"),
        "end": end_date.strftime("%Y/%m/%d"),
    }


def _resolve_financial_rule(transaction: Transaction):
    if transaction.activity is None:
        raise HTTPException(
            status_code=404,
            detail="No financial activity is linked to this transaction.",
        )

    financial_rule = next(
        (rule for rule in transaction.activity.financial_rules if rule.is_active),
        transaction.activity.financial_rules[0] if transaction.activity.financial_rules else None,
    )
    if financial_rule is None:
        raise HTTPException(
            status_code=404,
            detail="No financial rule is configured for the transaction activity.",
        )
    return financial_rule


def _resolve_work_period(db: Session, transaction: Transaction) -> WorkPeriod | None:
    work_period_id = _extract_work_period_id(transaction)
    if work_period_id is None:
        return None

    return db.query(WorkPeriod).filter(WorkPeriod.id == work_period_id).first()


def _resolve_year_month(
    transaction: Transaction,
    work_period: WorkPeriod | None,
) -> tuple[str, str]:
    if work_period is not None:
        return str(work_period.year), str(work_period.month).zfill(2)

    form_data = transaction.form_data if isinstance(transaction.form_data, dict) else {}

    raw_year = str(transaction.fiscal_year or form_data.get("year") or "").strip()
    if not raw_year.isdigit():
        raw_year = str(jdatetime.date.today().year)

    raw_month = form_data.get("month")
    try:
        month = int(raw_month)
    except (TypeError, ValueError):
        month = int(jdatetime.date.today().month)

    month = min(max(month, 1), 12)
    return raw_year, str(month).zfill(2)


def _build_cost_center_fragment(cost_center_code: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]", "", (cost_center_code or "").upper())
    return (normalized or "GEN").strip()[:8]


def _generate_allocation_unique_code(
    db: Session,
    *,
    transaction: Transaction,
    cost_center_code: str,
    work_period: WorkPeriod | None,
) -> str:
    year, month = _resolve_year_month(transaction, work_period)
    cost_center_fragment = _build_cost_center_fragment(cost_center_code)

    while True:
        suffix = uuid.uuid4().hex[:8].upper()
        candidate = f"HR-{year}{month}-{cost_center_fragment}-{suffix}"
        exists = (
            db.query(TransactionAllocation.id)
            .filter(TransactionAllocation.unique_code == candidate)
            .first()
        )
        if exists is None:
            return candidate


def _allocation_to_context_line(
    allocation: TransactionAllocation,
    *,
    financial_event_type: str,
) -> dict[str, object]:
    return {
        "id": allocation.id,
        "org_unit_name": allocation.org_unit_name,
        "cost_center_code": allocation.cost_center_code,
        "budget_line_code": allocation.budget_line_code,
        "financial_event_type": financial_event_type,
        "allocated_amount": float(allocation.allocated_amount),
        "legal_deductions": float(allocation.legal_deductions),
        "penalties": float(allocation.penalties),
        "net_amount": float(allocation.net_amount),
        "unique_code": allocation.unique_code,
    }


def _get_workflow_transaction_or_404(db: Session, transaction_id: int) -> Transaction:
    transaction = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.activity).joinedload(Activity.financial_rules),
        )
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return transaction


@router.get("/workflow/{transaction_id}/context", response_model=HRFinanceWorkflowContextOut)
def get_workflow_context(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = _get_workflow_transaction_or_404(db, transaction_id)

    work_period_id = _extract_work_period_id(transaction)
    if work_period_id is None:
        raise HTTPException(
            status_code=404,
            detail="No linked work period context was found for this transaction.",
        )

    work_period_row = (
        db.query(WorkPeriod, ContractorStatement, User)
        .outerjoin(ContractorStatement, ContractorStatement.work_period_id == WorkPeriod.id)
        .outerjoin(RegionalAttendanceSheet, ContractorStatement.sheet_id == RegionalAttendanceSheet.id)
        .outerjoin(User, RegionalAttendanceSheet.created_by_id == User.id)
        .filter(WorkPeriod.id == work_period_id)
        .order_by(ContractorStatement.created_at.desc(), ContractorStatement.id.desc())
        .first()
    )
    if work_period_row is None:
        raise HTTPException(status_code=404, detail="Linked work period not found.")

    work_period, _, contractor_user = work_period_row
    financial_rule = _resolve_financial_rule(transaction)
    form_data = transaction.form_data if isinstance(transaction.form_data, dict) else {}
    contractor_name = contractor_user.full_name if contractor_user else form_data.get("contractor_name")

    stored_allocations = (
        db.query(TransactionAllocation)
        .filter(TransactionAllocation.transaction_id == transaction.id)
        .order_by(TransactionAllocation.id.asc())
        .all()
    )

    payload = {
        "transaction": {
            "id": transaction.id,
            "status": transaction.status,
            "gross_amount": transaction.amount,
            "activity_id": transaction.activity_id,
            "activity_name": transaction.activity.name,
            "contract_number": transaction.contract_number,
        },
        "operational_context": {
            "work_period_id": work_period.id,
            "name": f"کارکرد {work_period.year}/{str(work_period.month).zfill(2)}",
            "year": work_period.year,
            "month": work_period.month,
            "date_range": _build_work_period_date_range(work_period.year, work_period.month),
            "contractor_name": contractor_name,
            "contract_number": transaction.contract_number,
        },
        "financial_rules": {
            "cost_center_code": financial_rule.cost_center_code,
            "budget_line_code": financial_rule.budget_line_code,
            "financial_event_type": financial_rule.financial_event_type,
        },
        "allocation_lines": [
            _allocation_to_context_line(
                allocation,
                financial_event_type=financial_rule.financial_event_type,
            )
            for allocation in stored_allocations
        ]
        or None,
    }
    logger.info(
        "HR finance workflow context for transaction %s requested by user %s: %s",
        transaction_id,
        current_user.id,
        json.dumps(payload, ensure_ascii=False, default=str),
    )
    return payload


@router.post(
    "/workflow/{transaction_id}/finalize",
    response_model=list[GeneratedHRTransactionCodeOut],
)
def finalize_workflow_transaction(
    transaction_id: int,
    payload: HRFinanceFinalizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = _get_workflow_transaction_or_404(db, transaction_id)
    _resolve_financial_rule(transaction)

    existing_allocations = (
        db.query(TransactionAllocation)
        .filter(TransactionAllocation.transaction_id == transaction.id)
        .order_by(TransactionAllocation.id.asc())
        .all()
    )
    if existing_allocations:
        return [
            GeneratedHRTransactionCodeOut(region=allocation.org_unit_name, code=allocation.unique_code)
            for allocation in existing_allocations
        ]

    if transaction.status not in ALLOWED_FINALIZE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=(
                "This transaction cannot be finalized from the HR finance workflow "
                f"while it is in '{transaction.status}' status."
            ),
        )

    gross_amount = Decimal(str(transaction.amount or 0))
    if gross_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Transaction gross amount must be greater than zero before finalization.",
        )

    submitted_total = sum(
        (allocation.allocated_amount for allocation in payload.allocations),
        Decimal("0"),
    )
    if submitted_total != gross_amount:
        raise HTTPException(
            status_code=400,
            detail=(
                "The sum of allocated amounts must equal the transaction gross amount. "
                f"Expected {gross_amount}, received {submitted_total}."
            ),
        )

    work_period = _resolve_work_period(db, transaction)
    if _extract_work_period_id(transaction) is not None and work_period is None:
        raise HTTPException(status_code=404, detail="Linked work period not found.")

    generated_allocations: list[TransactionAllocation] = []
    for allocation_in in payload.allocations:
        allocated_amount = allocation_in.allocated_amount
        legal_deductions = allocation_in.legal_deductions
        penalties = allocation_in.penalties
        net_amount = allocated_amount - legal_deductions - penalties
        if net_amount < 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Net amount cannot be negative after deductions and penalties "
                    f"for '{allocation_in.org_unit_name}'."
                ),
            )

        generated_allocations.append(
            TransactionAllocation(
                transaction_id=transaction.id,
                org_unit_name=allocation_in.org_unit_name.strip(),
                cost_center_code=allocation_in.cost_center_code.strip(),
                budget_line_code=allocation_in.budget_line_code.strip(),
                allocated_amount=allocated_amount,
                legal_deductions=legal_deductions,
                penalties=penalties,
                net_amount=net_amount,
                unique_code=_generate_allocation_unique_code(
                    db,
                    transaction=transaction,
                    cost_center_code=allocation_in.cost_center_code,
                    work_period=work_period,
                ),
            )
        )

    try:
        for allocation in generated_allocations:
            db.add(allocation)

        primary_code = generated_allocations[0].unique_code
        transaction.status = FINAL_TRANSACTION_STATUS
        transaction.current_approval_level = 4
        transaction.reviewed_by_id = current_user.id
        transaction.reviewed_at = datetime.utcnow()
        transaction.unique_code = primary_code

        if work_period is not None:
            work_period.status = WorkFlowStatus.SENT_TO_FINANCE
            work_period.financial_unique_code = primary_code

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Failed to finalize HR finance transaction %s for user %s.",
            transaction_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize HR finance transaction: {exc}",
        ) from exc

    logger.info(
        "HR finance transaction %s finalized by user %s with %s allocation(s).",
        transaction_id,
        current_user.id,
        len(generated_allocations),
    )
    return [
        GeneratedHRTransactionCodeOut(region=allocation.org_unit_name, code=allocation.unique_code)
        for allocation in generated_allocations
    ]
