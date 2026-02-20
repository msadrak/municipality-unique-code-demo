"""
Executive Reports Router - Sprint 4
=====================================

Provides aggregated financial data for the Executive Dashboard.

Endpoints:
  GET /reports/summary  — Top-level KPIs + departmental breakdown + section pie data
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    BudgetRow,
    Contract,
    ContractStatus,
    ProgressStatement,
    ProgressStatementStatus,
    OrgUnit,
)
from app.routers.auth import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


# ============================================================
# GET /reports/summary — Executive Dashboard data
# ============================================================

@router.get("/summary")
def get_executive_summary(db: Session = Depends(get_db)):
    """
    Aggregate financial KPIs for the Executive Dashboard.

    Returns:
    - total_budget:      Sum of all approved amounts (BudgetRow)
    - committed_funds:   Sum of all blocked amounts (active contract reservations)
    - executed_funds:    Sum of all spent amounts (paid statements)
    - active_contracts:  Count of non-draft/non-rejected contracts
    - contract_value:    Total value of active contracts
    - paid_statements:   Total net amount of PAID progress statements
    - by_department:     Budget / Committed / Spent grouped by OrgUnit
    - by_section:        Contract amounts grouped by OrgUnit (for pie chart)
    """

    # ------------------------------------------------------------------
    # 1. Top-level budget aggregates from BudgetRow (source of truth)
    # ------------------------------------------------------------------
    budget_totals = db.query(
        func.coalesce(func.sum(BudgetRow.approved_amount), 0).label("total_budget"),
        func.coalesce(func.sum(BudgetRow.blocked_amount), 0).label("committed"),
        func.coalesce(func.sum(BudgetRow.spent_amount), 0).label("spent"),
    ).first()

    total_budget = int(budget_totals.total_budget) if budget_totals else 0
    committed_funds = int(budget_totals.committed) if budget_totals else 0
    executed_funds = int(budget_totals.spent) if budget_totals else 0

    # ------------------------------------------------------------------
    # 2. Contract-level supplementary metrics
    # ------------------------------------------------------------------
    active_statuses = [
        ContractStatus.APPROVED,
        ContractStatus.NOTIFIED,
        ContractStatus.IN_PROGRESS,
        ContractStatus.PENDING_COMPLETION,
        ContractStatus.COMPLETED,
        ContractStatus.GUARANTEE_PERIOD,
        ContractStatus.PENDING_APPROVAL,
    ]

    contract_agg = db.query(
        func.count(Contract.id).label("count"),
        func.coalesce(func.sum(Contract.total_amount), 0).label("value"),
        func.coalesce(func.sum(Contract.paid_amount), 0).label("paid"),
    ).filter(
        Contract.status.in_(active_statuses)
    ).first()

    active_contracts = int(contract_agg.count) if contract_agg else 0
    contract_value = int(contract_agg.value) if contract_agg else 0
    contracts_paid = int(contract_agg.paid) if contract_agg else 0

    # ------------------------------------------------------------------
    # 3. Paid statements total
    # ------------------------------------------------------------------
    paid_statements_total = db.query(
        func.coalesce(func.sum(ProgressStatement.net_amount), 0)
    ).filter(
        ProgressStatement.status == ProgressStatementStatus.PAID
    ).scalar()
    paid_statements_total = int(paid_statements_total) if paid_statements_total else 0

    # ------------------------------------------------------------------
    # 4. By Department — Budget / Committed / Spent (Bar Chart data)
    # ------------------------------------------------------------------
    dept_rows = (
        db.query(
            func.coalesce(OrgUnit.title, "عمومی").label("department"),
            func.sum(BudgetRow.approved_amount).label("budget"),
            func.sum(BudgetRow.blocked_amount).label("committed"),
            func.sum(BudgetRow.spent_amount).label("spent"),
        )
        .outerjoin(OrgUnit, BudgetRow.org_unit_id == OrgUnit.id)
        .group_by(func.coalesce(OrgUnit.title, "عمومی"))
        .order_by(func.sum(BudgetRow.approved_amount).desc())
        .all()
    )

    by_department = [
        {
            "department": row.department or "عمومی",
            "budget": int(row.budget or 0),
            "committed": int(row.committed or 0),
            "spent": int(row.spent or 0),
        }
        for row in dept_rows
    ]

    # ------------------------------------------------------------------
    # 5. By Section — Contract amounts by OrgUnit (Pie Chart data)
    # ------------------------------------------------------------------
    section_rows = (
        db.query(
            func.coalesce(OrgUnit.title, "سایر").label("section"),
            func.sum(Contract.total_amount).label("amount"),
        )
        .outerjoin(OrgUnit, Contract.org_unit_id == OrgUnit.id)
        .filter(Contract.status.in_(active_statuses))
        .group_by(func.coalesce(OrgUnit.title, "سایر"))
        .order_by(func.sum(Contract.total_amount).desc())
        .all()
    )

    by_section = [
        {
            "section": row.section or "سایر",
            "amount": int(row.amount or 0),
        }
        for row in section_rows
    ]

    # If no section data from contracts, fall back to budget distribution
    if not by_section and by_department:
        by_section = [
            {"section": d["department"], "amount": d["budget"]}
            for d in by_department
        ]

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------
    return {
        "total_budget": total_budget,
        "committed_funds": committed_funds,
        "executed_funds": executed_funds,
        "active_contracts": active_contracts,
        "contract_value": contract_value,
        "contracts_paid": contracts_paid,
        "paid_statements": paid_statements_total,
        "by_department": by_department,
        "by_section": by_section,
    }
