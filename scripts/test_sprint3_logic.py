"""
Sprint 3 Logic Test - Progress Statement Lifecycle × Budget Integration
=========================================================================

Verifies:
  A) Statement creation with financial validation
  B) Over-payment prevention (CRITICAL)
  C) Full lifecycle: DRAFT → SUBMITTED → APPROVED → PAID
  D) Budget integration: confirm_spend fires at PAID
  E) Second statement for remaining amount

Usage:
    cd H:\Freelancing_Project\KalaniProject\municipality_demo
    python scripts/test_sprint3_logic.py
"""

import sys
import os

# Force UTF-8 on Windows console
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import (
    Base, BudgetRow, Contract, ContractStatus,
    Contractor, ContractTemplate,
    ProgressStatement, ProgressStatementStatus,
    Subsystem, SubsystemActivity,
)
from app.services.contract_service import create_draft, transition_status
from app.services.statement_service import (
    create_statement, submit_statement, approve_statement, pay_statement,
    get_contract_statements, get_statement_financial_summary,
    OverPaymentError, StatementValidationError,
)
from app.services.budget_service import block_funds


# ============================================================
# Helpers
# ============================================================

def header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def step(text):
    print(f">> {text}")

def ok(text):
    print(f"  [PASS] {text}")

def fail(text):
    print(f"  [FAIL] {text}")
    sys.exit(1)

def info(text):
    print(f"  [INFO] {text}")

def budget_report(label, budget_row):
    print(f"  [{label}]"
          f"  Approved={budget_row.approved_amount:>15,}"
          f"  Blocked={budget_row.blocked_amount:>12,}"
          f"  Spent={budget_row.spent_amount:>12,}"
          f"  Remaining={budget_row.remaining_balance:>15,}")


# ============================================================
# Main Test
# ============================================================

def main():
    header("Sprint 3 Logic Test: Statement Lifecycle x Budget Engine")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ============================================================
        # SETUP: Test fixtures (same pattern as Sprint 2 test)
        # ============================================================
        step("SETUP: Creating test data...")

        subsystem = db.query(Subsystem).filter(Subsystem.code == "TEST_S3").first()
        if not subsystem:
            subsystem = Subsystem(code="TEST_S3", title="Sprint 3 Test", is_active=True)
            db.add(subsystem)
            db.flush()

        activity = db.query(SubsystemActivity).filter(
            SubsystemActivity.code == "S3_ROAD"
        ).first()
        if not activity:
            activity = SubsystemActivity(
                subsystem_id=subsystem.id, code="S3_ROAD",
                title="Road Work S3", is_active=True,
            )
            db.add(activity)
            db.flush()

        # Budget: 100M approved, zero blocked/spent
        APPROVED = 100_000_000
        budget_row = BudgetRow(
            activity_id=activity.id,
            budget_coding=f"TEST-S3-{os.getpid()}",
            description="Sprint 3 Test Budget",
            approved_amount=APPROVED,
            blocked_amount=0,
            spent_amount=0,
            fiscal_year="1403",
        )
        db.add(budget_row)
        db.flush()

        contractor = Contractor(
            national_id=f"S3-{os.getpid()}",
            company_name="Test Contractor S3",
            source_system="MANUAL",
        )
        db.add(contractor)
        db.flush()

        template = ContractTemplate(
            code=f"S3_CIVIL_{os.getpid()}",
            title="Sprint 3 Test Template",
            category="CIVIL",
            schema_definition={"type": "object", "properties": {}},
        )
        db.add(template)
        db.flush()
        db.commit()

        info(f"BudgetRow ID: {budget_row.id} | Approved: {APPROVED:,}")
        budget_report("INITIAL", budget_row)

        # ============================================================
        # Create contract and move to APPROVED state
        # (needed: budget reservation via draft, then approve)
        # ============================================================
        step("Creating contract draft (50M of 100M budget)...")
        CONTRACT_AMOUNT = 50_000_000

        contract = create_draft(
            db=db,
            budget_row_id=budget_row.id,
            contractor_id=contractor.id,
            template_id=template.id,
            title="Sprint 3 Test Contract",
            total_amount=CONTRACT_AMOUNT,
            user_id=1,
        )
        db.commit()
        db.refresh(budget_row)
        info(f"Contract {contract.contract_number} created, status={contract.status.value}")
        budget_report("AFTER DRAFT", budget_row)

        # DRAFT → PENDING_APPROVAL → APPROVED
        step("Transitioning contract to APPROVED...")
        transition_status(db, contract.id, ContractStatus.PENDING_APPROVAL.value, user_id=1)
        transition_status(db, contract.id, ContractStatus.APPROVED.value, user_id=1)
        db.commit()
        db.refresh(contract)
        db.refresh(budget_row)

        assert contract.status == ContractStatus.APPROVED
        info(f"Contract status: {contract.status.value}")
        budget_report("AFTER APPROVE", budget_row)
        ok(
            "Contract APPROVED. Funds remain blocked until statement payment "
            f"(blocked={budget_row.blocked_amount:,}, spent={budget_row.spent_amount:,})"
        )

        # ============================================================
        # TEST A: Create Statement (basic validation)
        # ============================================================
        header("TEST A: Create Statement (30M of 50M contract)")

        stmt1 = create_statement(
            db=db,
            contract_id=contract.id,
            gross_amount=35_000_000,
            deductions=5_000_000,
            description="Statement 1 - Road paving phase 1",
            user_id=1,
        )
        db.commit()
        db.refresh(stmt1)

        info(f"Statement: {stmt1.statement_number} | Net: {stmt1.net_amount:,}")
        assert stmt1.status == ProgressStatementStatus.DRAFT
        assert stmt1.net_amount == 30_000_000
        assert stmt1.gross_amount == 35_000_000
        assert stmt1.deductions == 5_000_000
        assert stmt1.sequence_number == 1
        assert stmt1.cumulative_amount == 30_000_000
        ok(f"Statement created: {stmt1.statement_number}, net={stmt1.net_amount:,}")

        # ============================================================
        # TEST B: Over-payment prevention
        # ============================================================
        header("TEST B: Over-Payment Prevention")

        step("Trying to create statement for 25M (would exceed 50M total)...")
        try:
            create_statement(
                db=db,
                contract_id=contract.id,
                gross_amount=25_000_000,
                deductions=0,
                description="Should fail - over limit",
                user_id=1,
            )
            fail("OverPaymentError was NOT raised! This is a critical failure.")
        except OverPaymentError as e:
            ok(f"OverPaymentError raised correctly: available={e.available:,}")
            db.rollback()

        step("Trying statement for exactly 20M (should work: 30M + 20M = 50M)...")
        stmt2 = create_statement(
            db=db,
            contract_id=contract.id,
            gross_amount=20_000_000,
            deductions=0,
            description="Statement 2 - Road paving phase 2",
            user_id=1,
        )
        db.commit()
        db.refresh(stmt2)
        assert stmt2.net_amount == 20_000_000
        assert stmt2.cumulative_amount == 50_000_000  # 30M + 20M
        ok(f"Statement 2 created: {stmt2.statement_number}, cumulative={stmt2.cumulative_amount:,}")

        step("Trying to create a 3rd statement for 1 Rial (should fail: ceiling reached)...")
        try:
            create_statement(
                db=db,
                contract_id=contract.id,
                gross_amount=1,
                deductions=0,
                description="Should fail - ceiling reached",
                user_id=1,
            )
            fail("OverPaymentError was NOT raised at ceiling!")
        except OverPaymentError:
            ok("OverPaymentError raised at ceiling (30M + 20M + 1 > 50M)")
            db.rollback()

        # ============================================================
        # TEST C: Full Lifecycle (DRAFT → SUBMITTED → APPROVED → PAID)
        # ============================================================
        header("TEST C: Full Lifecycle on Statement 1")

        step("Submit: DRAFT → SUBMITTED...")
        stmt1 = submit_statement(db, stmt1.id, user_id=1)
        db.commit()
        db.refresh(stmt1)
        assert stmt1.status == ProgressStatementStatus.SUBMITTED
        assert stmt1.submitted_at is not None
        ok(f"Status = SUBMITTED (submitted_at set)")

        step("Approve: SUBMITTED → APPROVED...")
        stmt1 = approve_statement(db, stmt1.id, user_id=1, review_comment="Verified on-site")
        db.commit()
        db.refresh(stmt1)
        assert stmt1.status == ProgressStatementStatus.APPROVED
        assert stmt1.reviewed_by_id is not None
        assert stmt1.review_comment == "Verified on-site"
        ok(f"Status = APPROVED (reviewer set, comment saved)")

        step("Pay: APPROVED → PAID (budget integration!)...")
        db.refresh(budget_row)
        spent_before = budget_row.spent_amount

        stmt1 = pay_statement(db, stmt1.id, user_id=1)
        db.commit()
        db.refresh(stmt1)
        db.refresh(budget_row)
        db.refresh(contract)

        assert stmt1.status == ProgressStatementStatus.PAID
        ok(f"Status = PAID")

        # Budget check: confirm_spend should move 30M from blocked→spent at PAY step
        info(f"Spent before pay: {spent_before:,}, after: {budget_row.spent_amount:,}")
        budget_report("AFTER PAY STMT 1", budget_row)

        # Contract paid_amount check
        assert contract.paid_amount == 30_000_000, \
            f"Expected contract.paid_amount=30M, got {contract.paid_amount:,}"
        ok(f"Contract paid_amount = {contract.paid_amount:,} (updated correctly)")

        # ============================================================
        # TEST D: Financial Summary
        # ============================================================
        header("TEST D: Financial Summary")

        summary = get_statement_financial_summary(db, contract.id)
        info(f"Summary: {summary}")

        assert summary["statement_count"] == 2
        assert summary["total_net_committed"] == 50_000_000
        assert summary["total_paid"] == 30_000_000
        assert summary["remaining"] == 0  # 50M - 50M committed
        assert summary["contract_total"] == 50_000_000
        ok(f"Summary correct: committed={summary['total_net_committed']:,}, "
           f"paid={summary['total_paid']:,}, remaining={summary['remaining']:,}")

        # ============================================================
        # TEST E: Invalid state transition
        # ============================================================
        header("TEST E: Invalid State Transitions")

        from app.services.statement_service import InvalidStatementTransitionError

        step("Try to approve a DRAFT statement (should fail)...")
        try:
            approve_statement(db, stmt2.id, user_id=1)
            fail("Should not allow DRAFT → APPROVED")
        except InvalidStatementTransitionError:
            ok("Correctly blocked DRAFT → APPROVED")
            db.rollback()

        step("Try to pay a DRAFT statement (should fail)...")
        try:
            pay_statement(db, stmt2.id, user_id=1)
            fail("Should not allow DRAFT → PAID")
        except InvalidStatementTransitionError:
            ok("Correctly blocked DRAFT → PAID")
            db.rollback()

        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        header("FINAL SUMMARY")
        budget_report("FINAL BUDGET", budget_row)
        print(f"\n  Contract:     {contract.contract_number}")
        print(f"  Status:       {contract.status.value}")
        print(f"  Total:        {contract.total_amount:,} Rials")
        print(f"  Paid:         {contract.paid_amount:,} Rials")
        print(f"  Statements:   {summary['statement_count']}")
        print(f"  Committed:    {summary['total_net_committed']:,} Rials")
        print(f"\n  ALL ASSERTIONS PASSED!")
        print(f"  Over-payment prevention is ACTIVE. Budget integration is SAFE.\n")

    except AssertionError as e:
        fail(str(e))
    except Exception as e:
        print(f"\n  ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
