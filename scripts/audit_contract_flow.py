"""
Forensic Contract Flow Audit
===========================

Simulates the full contract journey and prints exact database state at each step:
  Step 0: Initial BudgetRow state
  Step 1: Create draft contract (budget block expected)
  Step 2: Approve contract (budget should stay blocked)
  Step 3: Submit + approve statement
  Step 4: Pay statement (blocked -> spent expected)

Usage:
    python scripts/audit_contract_flow.py
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is importable when script runs from /scripts
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal, engine
from app.models import (
    Base,
    BudgetRow,
    Contract,
    ContractStatus,
    ContractTemplate,
    Contractor,
    ProgressStatement,
    Subsystem,
    SubsystemActivity,
    User,
)
from app.auth_utils import hash_password
from app.services.contract_service import create_draft, transition_status
from app.services.statement_service import (
    approve_statement,
    create_statement,
    pay_statement,
    submit_statement,
)


CONTRACT_AMOUNT = 120_000_000
STATEMENT_GROSS = 45_000_000
STATEMENT_DEDUCTIONS = 5_000_000


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def budget_state(db, budget_id: int) -> dict:
    row = db.query(BudgetRow).filter(BudgetRow.id == budget_id).first()
    if not row:
        raise RuntimeError(f"BudgetRow {budget_id} not found")
    return {
        "id": row.id,
        "budget_coding": row.budget_coding,
        "approved": int(row.approved_amount),
        "blocked": int(row.blocked_amount),
        "spent": int(row.spent_amount),
        "remaining": int(row.remaining_balance),
    }


def contract_state(db, contract_id: int) -> dict:
    c = db.query(Contract).filter(Contract.id == contract_id).first()
    if not c:
        raise RuntimeError(f"Contract {contract_id} not found")
    status = c.status.value if hasattr(c.status, "value") else str(c.status)
    return {
        "id": c.id,
        "contract_number": c.contract_number,
        "status": status,
        "total_amount": int(c.total_amount),
        "paid_amount": int(c.paid_amount or 0),
        "version": int(c.version or 1),
    }


def statement_state(db, statement_id: int) -> dict:
    s = db.query(ProgressStatement).filter(ProgressStatement.id == statement_id).first()
    if not s:
        raise RuntimeError(f"ProgressStatement {statement_id} not found")
    status = s.status.value if hasattr(s.status, "value") else str(s.status)
    return {
        "id": s.id,
        "statement_number": s.statement_number,
        "status": status,
        "gross_amount": int(s.gross_amount),
        "deductions": int(s.deductions or 0),
        "net_amount": int(s.net_amount),
        "version": int(s.version or 1),
    }


def print_budget(label: str, state: dict):
    print(f"[{label}] {ts()}")
    print(
        "  BudgetRow"
        f" id={state['id']}"
        f" code={state['budget_coding']}"
        f" approved={state['approved']:,}"
        f" blocked={state['blocked']:,}"
        f" spent={state['spent']:,}"
        f" remaining={state['remaining']:,}"
    )


def print_budget_delta(label: str, previous: dict, current: dict):
    print(
        f"  Delta ({label}):"
        f" blocked={current['blocked'] - previous['blocked']:+,}"
        f" spent={current['spent'] - previous['spent']:+,}"
        f" remaining={current['remaining'] - previous['remaining']:+,}"
    )


def print_contract(state: dict):
    print(
        "  Contract"
        f" id={state['id']}"
        f" number={state['contract_number']}"
        f" status={state['status']}"
        f" total_amount={state['total_amount']:,}"
        f" paid_amount={state['paid_amount']:,}"
        f" version={state['version']}"
    )


def print_statement(state: dict):
    print(
        "  Statement"
        f" id={state['id']}"
        f" number={state['statement_number']}"
        f" status={state['status']}"
        f" gross={state['gross_amount']:,}"
        f" deductions={state['deductions']:,}"
        f" net={state['net_amount']:,}"
        f" version={state['version']}"
    )


def setup_test_data(db):
    suffix = f"{int(datetime.now(timezone.utc).timestamp())}_{os.getpid()}"

    subsystem = db.query(Subsystem).filter(Subsystem.code == "AUDIT_CONTRACT").first()
    if not subsystem:
        subsystem = Subsystem(code="AUDIT_CONTRACT", title="Audit Contract Subsystem", is_active=True)
        db.add(subsystem)
        db.flush()

    activity = SubsystemActivity(
        subsystem_id=subsystem.id,
        code=f"AUDIT_ACTIVITY_{suffix}",
        title=f"Audit Activity {suffix}",
        is_active=True,
    )
    db.add(activity)
    db.flush()

    budget_row = BudgetRow(
        activity_id=activity.id,
        budget_coding=f"AUDIT-BUDGET-{suffix}",
        description="Forensic contract flow audit budget row",
        approved_amount=500_000_000,
        blocked_amount=0,
        spent_amount=0,
        fiscal_year="1403",
    )
    db.add(budget_row)
    db.flush()

    contractor = Contractor(
        national_id=f"AUDIT-NID-{suffix}",
        company_name=f"Audit Contractor {suffix}",
        source_system="MANUAL",
    )
    db.add(contractor)
    db.flush()

    template = ContractTemplate(
        code=f"AUDIT_TEMPLATE_{suffix}",
        title=f"Audit Template {suffix}",
        category="CIVIL",
        schema_definition={"type": "object", "properties": {}},
    )
    db.add(template)
    db.flush()

    db.commit()
    return budget_row.id, contractor.id, template.id


def resolve_actor_user_id(db) -> int:
    """
    Resolve a valid actor user for service calls.

    Priority:
    1) manager_road_14 (created by scripts/create_manager.py)
    2) first existing user
    3) create dedicated audit_actor user
    """
    manager = db.query(User).filter(User.username == "manager_road_14").first()
    if manager:
        return manager.id

    existing = db.query(User).order_by(User.id.asc()).first()
    if existing:
        return existing.id

    actor = User(
        username="audit_actor",
        password_hash=hash_password("admin"),
        full_name="Audit Actor",
        role="ADMIN_L2",
        admin_level=2,
        is_active=True,
    )
    db.add(actor)
    db.commit()
    db.refresh(actor)
    return actor.id


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("=" * 84)
        print("FORENSIC AUDIT: CONTRACT APPROVAL + STATEMENT PAYMENT")
        print("=" * 84)

        actor_user_id = resolve_actor_user_id(db)
        print(f"Actor user ID: {actor_user_id}")

        budget_id, contractor_id, template_id = setup_test_data(db)

        # Step 0
        s0 = budget_state(db, budget_id)
        print_budget("STEP 0 (INITIAL)", s0)
        print()

        # Step 1: draft
        contract = create_draft(
            db=db,
            budget_row_id=budget_id,
            contractor_id=contractor_id,
            template_id=template_id,
            title="Forensic Audit Contract",
            total_amount=CONTRACT_AMOUNT,
            user_id=actor_user_id,
            template_data={"audit_run": True},
        )
        db.commit()

        s1 = budget_state(db, budget_id)
        c1 = contract_state(db, contract.id)
        print_budget("STEP 1 (DRAFT CREATED)", s1)
        print_budget_delta("Step0 -> Step1", s0, s1)
        print_contract(c1)
        print(f"  Check: blocked increased after draft? {'YES' if s1['blocked'] > s0['blocked'] else 'NO'}")
        print()

        # Step 2: approve contract
        transition_status(db, contract.id, ContractStatus.PENDING_APPROVAL.value, user_id=actor_user_id)
        transition_status(db, contract.id, ContractStatus.APPROVED.value, user_id=actor_user_id)
        db.commit()

        s2 = budget_state(db, budget_id)
        c2 = contract_state(db, contract.id)
        print_budget("STEP 2 (CONTRACT APPROVED)", s2)
        print_budget_delta("Step1 -> Step2", s1, s2)
        print_contract(c2)
        print(f"  Check: blocked stayed same on approval? {'YES' if s2['blocked'] == s1['blocked'] else 'NO'}")
        print()

        # Step 3: statement submit
        statement = create_statement(
            db=db,
            contract_id=contract.id,
            gross_amount=STATEMENT_GROSS,
            deductions=STATEMENT_DEDUCTIONS,
            description="Forensic audit statement",
            user_id=actor_user_id,
        )
        submit_statement(db, statement.id, user_id=actor_user_id)
        db.commit()

        s3 = budget_state(db, budget_id)
        st3 = statement_state(db, statement.id)
        print_budget("STEP 3 (STATEMENT SUBMITTED)", s3)
        print_budget_delta("Step2 -> Step3", s2, s3)
        print_statement(st3)
        print(
            "  Check: statement is SUBMITTED?"
            f" {'YES' if st3['status'] == 'SUBMITTED' else 'NO'}"
        )
        print()

        # Step 4: pay statement
        # Pay requires APPROVED, so the script applies that precondition first.
        approve_statement(db, statement.id, user_id=actor_user_id, review_comment="Forensic audit approval")
        pay_statement(db, statement.id, user_id=actor_user_id)
        db.commit()

        s4 = budget_state(db, budget_id)
        c4 = contract_state(db, contract.id)
        st4 = statement_state(db, statement.id)
        print_budget("STEP 4 (STATEMENT PAID)", s4)
        print_budget_delta("Step3 -> Step4", s3, s4)
        print_contract(c4)
        print_statement(st4)
        print(
            "  Check: blocked decreased and spent increased on pay?"
            f" {'YES' if (s4['blocked'] < s3['blocked'] and s4['spent'] > s3['spent']) else 'NO'}"
        )
        print("=" * 84)
        print("AUDIT COMPLETE")
        print("=" * 84)
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
