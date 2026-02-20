"""
Sprint 3 Payment Verification Script
======================================

This script is the PROOF that the Progress Statement -> Budget integration works.

Tests:
  1. Finds or creates an APPROVED Contract with a linked BudgetRow.
  2. Creates a ProgressStatement for 50% of the contract amount.
  3. Walks the statement through DRAFT -> SUBMITTED -> APPROVED -> PAID.
  4. ASSERTION: BudgetRow "spent_amount" increases by exactly the statement net_amount.
  5. ASSERTION: A second statement exceeding the remaining balance is REJECTED.

Usage:
    cd H:\\Freelancing_Project\\KalaniProject\\municipality_demo
    python scripts/test_sprint3_payment.py
"""

import sys
import os

# Force UTF-8 on Windows console
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import (
    Base,
    BudgetRow,
    Contract,
    ContractStatus,
    Contractor,
    ContractTemplate,
    ProgressStatement,
    ProgressStatementStatus,
    Subsystem,
    SubsystemActivity,
)
from app.services.contract_service import create_draft, transition_status
from app.services.statement_service import (
    OverPaymentError,
    approve_statement,
    create_statement,
    pay_statement,
    submit_statement,
)


# ============================================================
# Display Helpers
# ============================================================

PASS_COUNT = 0
FAIL_COUNT = 0


def header(text: str):
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}")


def step(text: str):
    print(f"\n  >> {text}")


def ok(text: str):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"     [PASS] {text}")


def fail(text: str):
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"     [FAIL] {text}")


def info(text: str):
    print(f"     [INFO] {text}")


def budget_snapshot(label: str, row: BudgetRow):
    print(
        f"     [{label}]"
        f"  Approved={row.approved_amount:>15,}"
        f"  Blocked={row.blocked_amount:>12,}"
        f"  Spent={row.spent_amount:>12,}"
        f"  Remaining={row.remaining_balance:>15,}"
    )


# ============================================================
# Main Test
# ============================================================

def main():
    header("Sprint 3 Payment Proof: Statement Lifecycle x Budget Engine")

    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ===========================================================
        # PHASE 1 - SETUP: Create test fixtures
        # ===========================================================
        header("PHASE 1: Setup Test Fixtures")

        pid = os.getpid()  # unique suffix to avoid collisions

        # Subsystem & Activity
        subsystem = db.query(Subsystem).filter(Subsystem.code == "PAY_TEST").first()
        if not subsystem:
            subsystem = Subsystem(code="PAY_TEST", title="Payment Test Subsystem", is_active=True)
            db.add(subsystem)
            db.flush()

        activity = db.query(SubsystemActivity).filter(
            SubsystemActivity.code == "PAY_ROAD"
        ).first()
        if not activity:
            activity = SubsystemActivity(
                subsystem_id=subsystem.id,
                code="PAY_ROAD",
                title="Road Work - Payment Test",
                is_active=True,
            )
            db.add(activity)
            db.flush()

        # Budget Row: 200M Rials approved, clean slate
        BUDGET_APPROVED = 200_000_000
        budget_row = BudgetRow(
            activity_id=activity.id,
            budget_coding=f"PAYTEST-{pid}",
            description="Sprint 3 Payment Test Budget",
            approved_amount=BUDGET_APPROVED,
            blocked_amount=0,
            spent_amount=0,
            fiscal_year="1403",
        )
        db.add(budget_row)
        db.flush()

        contractor = Contractor(
            national_id=f"PAY-{pid}",
            company_name="Payment Test Contractor",
            source_system="MANUAL",
        )
        db.add(contractor)
        db.flush()

        template = ContractTemplate(
            code=f"PAY_TPL_{pid}",
            title="Payment Test Template",
            category="CIVIL",
            schema_definition={"type": "object", "properties": {}},
        )
        db.add(template)
        db.flush()
        db.commit()

        info(f"BudgetRow ID={budget_row.id}, Approved={BUDGET_APPROVED:,} Rials")
        budget_snapshot("INITIAL", budget_row)

        # ===========================================================
        # PHASE 2 - Create contract & move to APPROVED
        # ===========================================================
        header("PHASE 2: Create APPROVED Contract (100M of 200M budget)")

        CONTRACT_AMOUNT = 100_000_000
        USER_ID = 1

        contract = create_draft(
            db=db,
            budget_row_id=budget_row.id,
            contractor_id=contractor.id,
            template_id=template.id,
            title="Payment Test Contract",
            total_amount=CONTRACT_AMOUNT,
            user_id=USER_ID,
        )
        db.commit()
        db.refresh(budget_row)

        info(f"Contract {contract.contract_number} created (DRAFT)")
        budget_snapshot("AFTER DRAFT", budget_row)

        # DRAFT -> PENDING_APPROVAL -> APPROVED
        transition_status(db, contract.id, ContractStatus.PENDING_APPROVAL.value, user_id=USER_ID)
        transition_status(db, contract.id, ContractStatus.APPROVED.value, user_id=USER_ID)
        db.commit()
        db.refresh(contract)
        db.refresh(budget_row)

        assert contract.status == ContractStatus.APPROVED, \
            f"Expected APPROVED, got {contract.status}"
        info(f"Contract status = {contract.status.value}")
        budget_snapshot("AFTER APPROVE", budget_row)
        ok(f"Contract APPROVED. Blocked={budget_row.blocked_amount:,}, Spent={budget_row.spent_amount:,}")

        # ===========================================================
        # PHASE 3 - Create statement for 50% of contract
        # ===========================================================
        header("PHASE 3: Create Statement for 50% of Contract (50M)")

        STATEMENT_AMOUNT = CONTRACT_AMOUNT // 2  # 50M
        DEDUCTIONS = 5_000_000
        GROSS = STATEMENT_AMOUNT + DEDUCTIONS  # 55M

        step("Creating statement: gross=55M, deductions=5M, net=50M")
        stmt = create_statement(
            db=db,
            contract_id=contract.id,
            gross_amount=GROSS,
            deductions=DEDUCTIONS,
            description="Payment proof - Phase 1 road work",
            user_id=USER_ID,
            period_start=None,
            period_end=None,
        )
        db.commit()
        db.refresh(stmt)

        assert stmt.status == ProgressStatementStatus.DRAFT
        assert stmt.net_amount == STATEMENT_AMOUNT
        assert stmt.gross_amount == GROSS
        ok(f"Statement {stmt.statement_number} created (DRAFT). Net={stmt.net_amount:,}")

        # ===========================================================
        # PHASE 4 - Walk statement through lifecycle -> PAID
        # ===========================================================
        header("PHASE 4: Statement Lifecycle DRAFT -> SUBMITTED -> APPROVED -> PAID")

        # Record budget state BEFORE payment
        db.refresh(budget_row)
        spent_before_pay = budget_row.spent_amount
        blocked_before_pay = budget_row.blocked_amount
        info(f"Budget BEFORE pay: blocked={blocked_before_pay:,}, spent={spent_before_pay:,}")

        step("DRAFT -> SUBMITTED")
        stmt = submit_statement(db, stmt.id, user_id=USER_ID)
        db.commit()
        db.refresh(stmt)
        assert stmt.status == ProgressStatementStatus.SUBMITTED
        ok("Status = SUBMITTED")

        step("SUBMITTED -> APPROVED")
        stmt = approve_statement(db, stmt.id, user_id=USER_ID, review_comment="Verified on-site")
        db.commit()
        db.refresh(stmt)
        assert stmt.status == ProgressStatementStatus.APPROVED
        ok("Status = APPROVED")

        step("APPROVED -> PAID (this triggers confirm_spend!)")
        stmt = pay_statement(db, stmt.id, user_id=USER_ID)
        db.commit()
        db.refresh(stmt)
        db.refresh(budget_row)
        db.refresh(contract)

        assert stmt.status == ProgressStatementStatus.PAID
        ok("Status = PAID")

        # ===========================================================
        # ASSERTION 1: Budget "Spent" increased by exactly net_amount
        # ===========================================================
        header("ASSERTION 1: Budget Spent Increased by Exactly 50M")

        spent_after_pay = budget_row.spent_amount
        spent_delta = spent_after_pay - spent_before_pay

        budget_snapshot("AFTER PAY", budget_row)
        info(f"Spent before: {spent_before_pay:,}")
        info(f"Spent after:  {spent_after_pay:,}")
        info(f"Delta:        {spent_delta:,}")
        info(f"Expected:     {STATEMENT_AMOUNT:,}")

        if spent_delta == STATEMENT_AMOUNT:
            ok(f"CRITICAL ASSERTION PASSED: spent_delta ({spent_delta:,}) == statement_net ({STATEMENT_AMOUNT:,})")
        else:
            fail(
                f"CRITICAL ASSERTION FAILED: spent_delta ({spent_delta:,}) != "
                f"statement_net ({STATEMENT_AMOUNT:,})"
            )

        # Also verify contract.paid_amount
        if contract.paid_amount == STATEMENT_AMOUNT:
            ok(f"Contract paid_amount = {contract.paid_amount:,} (correct)")
        else:
            fail(f"Contract paid_amount = {contract.paid_amount:,}, expected {STATEMENT_AMOUNT:,}")

        # Verify blocked decreased by the same amount
        blocked_after_pay = budget_row.blocked_amount
        blocked_delta = blocked_before_pay - blocked_after_pay
        if blocked_delta == STATEMENT_AMOUNT:
            ok(f"Blocked decreased by {blocked_delta:,} (blocked->spent confirmed)")
        else:
            fail(f"Blocked delta = {blocked_delta:,}, expected {STATEMENT_AMOUNT:,}")

        # ===========================================================
        # ASSERTION 2: Overpayment Prevention
        # ===========================================================
        header("ASSERTION 2: Second Statement Exceeding Remaining Balance -> ERROR")

        remaining_ceiling = CONTRACT_AMOUNT - STATEMENT_AMOUNT  # 50M left
        overshoot_amount = remaining_ceiling + 1  # 50,000,001 Rials

        step(f"Remaining contract ceiling: {remaining_ceiling:,} Rials")
        step(f"Attempting to create statement for {overshoot_amount:,} Rials (exceeds by 1)...")

        try:
            create_statement(
                db=db,
                contract_id=contract.id,
                amount=overshoot_amount,
                description="Should FAIL - over remaining balance",
                user_id=USER_ID,
            )
            fail(
                f"OverPaymentError was NOT raised! "
                f"A statement for {overshoot_amount:,} was accepted on a contract "
                f"with only {remaining_ceiling:,} remaining."
            )
        except OverPaymentError as e:
            ok(
                f"OverPaymentError raised correctly: "
                f"requested={e.requested:,}, available={e.available:,}"
            )
            db.rollback()

        # Also test: exact remaining amount SHOULD succeed
        step(f"Creating statement for exactly remaining {remaining_ceiling:,} Rials (should work)...")
        stmt2 = create_statement(
            db=db,
            contract_id=contract.id,
            amount=remaining_ceiling,
            description="Statement 2 - exact remaining balance",
            user_id=USER_ID,
        )
        db.commit()
        db.refresh(stmt2)
        assert stmt2.net_amount == remaining_ceiling
        ok(f"Statement 2 accepted for exactly {remaining_ceiling:,} (ceiling now fully used)")

        # One more attempt: even 1 Rial should fail now
        step("Attempting 1 Rial statement (ceiling is fully used)...")
        try:
            create_statement(
                db=db,
                contract_id=contract.id,
                amount=1,
                description="Should FAIL - ceiling fully used",
                user_id=USER_ID,
            )
            fail("OverPaymentError was NOT raised at 100% ceiling usage!")
        except OverPaymentError:
            ok("OverPaymentError raised at 100% ceiling (0 Rials remaining)")
            db.rollback()

        # ===========================================================
        # FINAL SUMMARY
        # ===========================================================
        header("FINAL SUMMARY")

        db.refresh(budget_row)
        budget_snapshot("FINAL BUDGET", budget_row)
        print(f"\n     Contract:        {contract.contract_number}")
        print(f"     Status:          {contract.status.value}")
        print(f"     Total Amount:    {contract.total_amount:,} Rials")
        print(f"     Paid Amount:     {contract.paid_amount:,} Rials")
        print(f"     Statement 1:     {stmt.statement_number} -> PAID ({stmt.net_amount:,} Rials)")
        print(f"     Statement 2:     {stmt2.statement_number} -> DRAFT ({stmt2.net_amount:,} Rials)")
        print()
        print(f"     PASS: {PASS_COUNT}")
        print(f"     FAIL: {FAIL_COUNT}")
        print()

        if FAIL_COUNT == 0:
            print("     ============================================")
            print("     ALL ASSERTIONS PASSED!")
            print("     Over-payment prevention is ACTIVE.")
            print("     Budget integration (confirm_spend) is SAFE.")
            print("     Sprint 3 is VERIFIED.")
            print("     ============================================")
        else:
            print("     !! SOME ASSERTIONS FAILED - SEE ABOVE !!")
            sys.exit(1)

    except AssertionError as e:
        fail(f"AssertionError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n     UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
