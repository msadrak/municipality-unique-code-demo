"""
Sprint 2 Logic Test - Contract Lifecycle x Budget Integration
===============================================================

Verifies the financial safety of the contract state machine by testing:
  A) Draft creation -> budget reservation (remaining drops)
  B) Rejection -> budget release (remaining returns)
  C) Re-approval -> budget permanent lock (remaining drops, confirms spend)

Usage:
    cd H:\Freelancing_Project\KalaniProject\municipality_demo
    python scripts/test_sprint2_logic.py
"""

import sys
import os

# Force UTF-8 on Windows console (needed for Persian text in test data)
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
    Subsystem, SubsystemActivity,
)
from app.services.contract_service import (
    create_draft, transition_status,
    ContractNotFoundError, InvalidTransitionError, ContractValidationError,
)
from app.services.budget_service import block_funds

# ============================================================
# ANSI Colors for terminal output
# ============================================================
GREEN  = ""
RED    = ""
YELLOW = ""
CYAN   = ""
BOLD   = ""
RESET  = ""

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
    """Print a clean budget status line."""
    print(f"  {BOLD}[{label}]{RESET}"
          f"  Approved={budget_row.approved_amount:>15,}"
          f"  Blocked={budget_row.blocked_amount:>12,}"
          f"  Spent={budget_row.spent_amount:>12,}"
          f"  Remaining={budget_row.remaining_balance:>15,}")


# ============================================================
# Main Test Scenario
# ============================================================

def main():
    header("Sprint 2 Logic Test: Contract Lifecycle × Budget Engine")

    # --- Create all tables ---
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ============================================================
        # SETUP: Create test fixtures
        # ============================================================
        step("SETUP: Creating test data...")

        # Subsystem + Activity (required by BudgetRow FK)
        subsystem = db.query(Subsystem).filter(Subsystem.code == "TEST_CTR").first()
        if not subsystem:
            subsystem = Subsystem(code="TEST_CTR", title="سامانه تست قرارداد", is_active=True)
            db.add(subsystem)
            db.flush()

        activity = db.query(SubsystemActivity).filter(
            SubsystemActivity.code == "ROAD_MAINTENANCE"
        ).first()
        if not activity:
            activity = SubsystemActivity(
                subsystem_id=subsystem.id,
                code="ROAD_MAINTENANCE",
                title="نگهداری راه",
                is_active=True,
            )
            db.add(activity)
            db.flush()

        # BudgetRow: 100,000,000 Rials (100M)
        APPROVED_AMOUNT = 100_000_000
        budget_row = BudgetRow(
            activity_id=activity.id,
            budget_coding=f"TEST-S2-{os.getpid()}",  # unique per run
            description="ردیف بودجه تست - نگهداری راه",
            approved_amount=APPROVED_AMOUNT,
            blocked_amount=0,
            spent_amount=0,
            fiscal_year="1403",
        )
        db.add(budget_row)
        db.flush()

        # Contractor
        contractor = Contractor(
            national_id=f"TEST-{os.getpid()}",
            company_name="شرکت تست عمران",
            source_system="MANUAL",
        )
        db.add(contractor)
        db.flush()

        # ContractTemplate
        template = ContractTemplate(
            code=f"TEST_CIVIL_{os.getpid()}",
            title="قالب تست عمرانی",
            category="CIVIL",
            schema_definition={
                "type": "object",
                "properties": {
                    "project_location": {"type": "string", "title": "محل پروژه"},
                    "duration_days": {"type": "integer", "title": "مدت (روز)"},
                },
                "required": ["project_location"],
            },
        )
        db.add(template)
        db.flush()

        db.commit()

        info(f"BudgetRow ID: {budget_row.id}  |  Coding: {budget_row.budget_coding}")
        info(f"Contractor ID: {contractor.id}  |  Name: {contractor.company_name}")
        info(f"Template ID: {template.id}  |  Code: {template.code}")

        # Refresh to get clean state
        db.refresh(budget_row)
        budget_report("INITIAL", budget_row)

        assert budget_row.remaining_balance == APPROVED_AMOUNT, \
            f"Expected {APPROVED_AMOUNT}, got {budget_row.remaining_balance}"
        ok(f"Initial remaining = {APPROVED_AMOUNT:,} ریال")

        # ============================================================
        # STEP A: Draft Creation → Budget Reservation
        # ============================================================
        header("STEP A: Draft Creation (Budget Reservation)")

        CONTRACT_AMOUNT = 20_000_000   # 20M
        EXPECTED_AFTER_BLOCK = APPROVED_AMOUNT - CONTRACT_AMOUNT  # 80M

        step(f"Creating contract draft for {CONTRACT_AMOUNT:,} Rials...")

        contract = create_draft(
            db=db,
            budget_row_id=budget_row.id,
            contractor_id=contractor.id,
            template_id=template.id,
            title="قرارداد تست نگهداری راه - فاز ۱",
            total_amount=CONTRACT_AMOUNT,
            user_id=1,  # system user
            template_data={"project_location": "بزرگراه همت", "duration_days": 90},
        )
        db.commit()
        db.refresh(budget_row)
        db.refresh(contract)

        info(f"Contract created: {contract.contract_number}  |  Status: {contract.status.value}")
        budget_report("AFTER DRAFT", budget_row)

        # Assert: Contract exists
        assert contract.id is not None, "Contract was not created"
        ok(f"Contract {contract.contract_number} created successfully")

        # Assert: Status is DRAFT
        assert contract.status == ContractStatus.DRAFT, \
            f"Expected DRAFT, got {contract.status}"
        ok("Status = DRAFT")

        # Assert: Budget reserved (remaining dropped)
        assert budget_row.remaining_balance == EXPECTED_AFTER_BLOCK, \
            f"Expected remaining={EXPECTED_AFTER_BLOCK:,}, got {budget_row.remaining_balance:,}"
        ok(f"Remaining dropped: {APPROVED_AMOUNT:,} → {budget_row.remaining_balance:,} (reservation of {CONTRACT_AMOUNT:,} worked)")

        # ============================================================
        # STEP B: Rejection → Budget Release
        # ============================================================
        header("STEP B: Rejection (Budget Release)")

        # DRAFT → PENDING_APPROVAL
        step("Transitioning DRAFT → PENDING_APPROVAL...")
        contract = transition_status(db, contract.id, ContractStatus.PENDING_APPROVAL.value, user_id=1)
        db.commit()
        db.refresh(contract)
        db.refresh(budget_row)

        info(f"Status: {contract.status.value}")
        budget_report("AFTER SUBMIT", budget_row)
        ok("Status = PENDING_APPROVAL")

        # PENDING_APPROVAL → REJECTED (should release funds)
        step("Transitioning PENDING_APPROVAL → REJECTED...")
        contract = transition_status(db, contract.id, ContractStatus.REJECTED.value, user_id=1)
        db.commit()
        db.refresh(budget_row)
        db.refresh(contract)

        info(f"Status: {contract.status.value}")
        budget_report("AFTER REJECT", budget_row)

        # Assert: Status is REJECTED
        assert contract.status == ContractStatus.REJECTED, \
            f"Expected REJECTED, got {contract.status}"
        ok("Status = REJECTED")

        # Assert: Budget released (remaining returned)
        assert budget_row.remaining_balance == APPROVED_AMOUNT, \
            f"Expected remaining={APPROVED_AMOUNT:,} (full release), got {budget_row.remaining_balance:,}"
        ok(f"Remaining returned: {EXPECTED_AFTER_BLOCK:,} → {budget_row.remaining_balance:,} (funds released!)")

        # ============================================================
        # STEP C: Re-Approval → Budget Permanent Lock
        # ============================================================
        header("STEP C: Re-Approval (Budget Permanent Lock)")

        # REJECTED → DRAFT (re-enter the wizard)
        step("Transitioning REJECTED → DRAFT (re-draft)...")
        contract = transition_status(db, contract.id, ContractStatus.DRAFT.value, user_id=1)
        db.commit()
        db.refresh(contract)
        info(f"Status: {contract.status.value}")
        ok("Status = DRAFT (re-entered)")

        # Re-block funds (simulates re-reservation on re-draft)
        step(f"Re-reserving {CONTRACT_AMOUNT:,} Rials in budget...")
        block_funds(
            db=db,
            budget_id=budget_row.id,
            amount=CONTRACT_AMOUNT,
            user_id="1",
            reference_doc=f"Contract-{contract.contract_number}-redraft",
            notes="رزرو مجدد بودجه پس از بازگشت از رد",
        )
        db.commit()
        db.refresh(budget_row)
        budget_report("AFTER RE-BLOCK", budget_row)

        assert budget_row.remaining_balance == EXPECTED_AFTER_BLOCK, \
            f"Expected {EXPECTED_AFTER_BLOCK:,}, got {budget_row.remaining_balance:,}"
        ok(f"Budget re-reserved: {APPROVED_AMOUNT:,} → {budget_row.remaining_balance:,}")

        # DRAFT → PENDING_APPROVAL
        step("Transitioning DRAFT → PENDING_APPROVAL...")
        contract = transition_status(db, contract.id, ContractStatus.PENDING_APPROVAL.value, user_id=1)
        db.commit()
        db.refresh(contract)
        info(f"Status: {contract.status.value}")

        # PENDING_APPROVAL → APPROVED (should confirm_spend: blocked → spent)
        step("Transitioning PENDING_APPROVAL → APPROVED (permanent lock!)...")
        contract = transition_status(db, contract.id, ContractStatus.APPROVED.value, user_id=1)
        db.commit()
        db.refresh(budget_row)
        db.refresh(contract)

        info(f"Status: {contract.status.value}")
        budget_report("AFTER APPROVE", budget_row)

        # Assert: Status is APPROVED
        assert contract.status == ContractStatus.APPROVED, \
            f"Expected APPROVED, got {contract.status}"
        ok("Status = APPROVED")

        # Assert: Remaining dropped (permanent lock)
        assert budget_row.remaining_balance == EXPECTED_AFTER_BLOCK, \
            f"Expected {EXPECTED_AFTER_BLOCK:,}, got {budget_row.remaining_balance:,}"
        ok(f"Remaining = {budget_row.remaining_balance:,} (permanently locked)")

        # Assert: blocked → spent (confirm_spend moved it)
        assert budget_row.blocked_amount == 0, \
            f"Expected blocked=0 after approval, got {budget_row.blocked_amount:,}"
        ok(f"Blocked = 0 (moved to spent)")

        assert budget_row.spent_amount >= CONTRACT_AMOUNT, \
            f"Expected spent >= {CONTRACT_AMOUNT:,}, got {budget_row.spent_amount:,}"
        ok(f"Spent = {budget_row.spent_amount:,} (budget permanently committed)")

        # Assert: Credit system mock received the request
        credit_meta = contract.metadata_extra or {}
        credit_ref = credit_meta.get("credit_ref_id", "")
        assert credit_ref.startswith("CRED-MOCK-"), \
            f"Expected CRED-MOCK-xxx, got '{credit_ref}'"
        ok(f"CreditSystemPort mock ref: {credit_ref}")

        # ============================================================
        # FINAL SUMMARY
        # ============================================================
        header("FINAL SUMMARY")
        budget_report("FINAL STATE", budget_row)
        print(f"\n  {BOLD}Contract:{RESET}  {contract.contract_number}")
        print(f"  {BOLD}Status:{RESET}    {contract.status.value}")
        print(f"  {BOLD}Amount:{RESET}    {contract.total_amount:,} Rials")
        print(f"\n  ALL 7 ASSERTIONS PASSED!")
        print(f"  The financial engine is SAFE. Budget invariants hold.\n")

    except AssertionError as e:
        fail(str(e))
    except Exception as e:
        print(f"\n  {RED}ERROR: {type(e).__name__}: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
