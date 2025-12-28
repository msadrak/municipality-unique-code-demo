"""
Inject Test Budget Data
========================

This script manually inserts test BudgetRow records for the "Land Acquisition" 
activity to prove the Frontend/API works when data exists.

This is a DIAGNOSTIC script - not for production use.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import BudgetRow, SubsystemActivity, OrgUnit


def find_activity_by_title_keyword(db: Session, keyword: str) -> SubsystemActivity | None:
    """Find activity by partial title match."""
    return db.query(SubsystemActivity).filter(
        SubsystemActivity.title.ilike(f"%{keyword}%")
    ).first()


def find_zone_by_code(db: Session, code: str) -> OrgUnit | None:
    """Find org unit (zone) by code."""
    return db.query(OrgUnit).filter(OrgUnit.code == code).first()


def inject_test_data(db: Session):
    """Inject test budget rows for Land Acquisition activity."""
    
    print("\n" + "="*60)
    print("  INJECTING TEST BUDGET DATA")
    print("="*60)
    
    # Step 1: Find the Land Acquisition activity
    activity = find_activity_by_title_keyword(db, "تملک")
    
    if not activity:
        print("❌ ERROR: Could not find 'Land Acquisition' (تملک) activity!")
        print("   Please run the seeder first: python seed_full_system.py")
        return False
    
    print(f"\n✅ Found Activity:")
    print(f"   ID: {activity.id}")
    print(f"   Title: {activity.title}")
    print(f"   Code: {activity.code}")
    print(f"   Subsystem ID: {activity.subsystem_id}")
    
    # Step 2: Find Zone 1 (منطقه یک)
    zone_1 = db.query(OrgUnit).filter(OrgUnit.id == 1).first()
    
    if zone_1:
        print(f"\n✅ Found Zone 1:")
        print(f"   ID: {zone_1.id}")
        print(f"   Title: {zone_1.title}")
        print(f"   Code: {zone_1.code}")
    else:
        print("\n⚠️  Zone 1 not found, will use org_unit_id=1 anyway")
    
    # Step 3: Check if test data already exists
    existing = db.query(BudgetRow).filter(
        BudgetRow.activity_id == activity.id,
        BudgetRow.budget_coding.like("TEST_%")
    ).all()
    
    if existing:
        print(f"\n⚠️  Test data already exists ({len(existing)} rows). Skipping insertion.")
        print("   To re-inject, delete existing test rows first:")
        for row in existing:
            print(f"      - ID={row.id}: {row.budget_coding}")
        return True
    
    # Step 4: Create test budget rows
    print("\n📝 Creating test budget rows...")
    
    # Row A: For Region 1 (org_unit_id=1)
    row_a = BudgetRow(
        activity_id=activity.id,
        org_unit_id=1,  # Region 1
        budget_coding="TEST_LAND_ACQ_REGION1",
        description="تملک اراضی - منطقه یک (TEST DATA)",
        approved_amount=100_000_000_000,  # 100 Billion Rials (100M Toman)
        blocked_amount=0,
        spent_amount=20_000_000_000,  # 20 Billion spent
        fiscal_year="1403"
    )
    
    # Row B: Global HQ (org_unit_id=NULL)
    row_b = BudgetRow(
        activity_id=activity.id,
        org_unit_id=None,  # Global HQ - accessible by all zones
        budget_coding="TEST_LAND_ACQ_GLOBAL",
        description="تملک اراضی - ستاد مرکزی (TEST DATA)",
        approved_amount=500_000_000_000,  # 500 Billion Rials (500M Toman)
        blocked_amount=50_000_000_000,  # 50 Billion blocked
        spent_amount=100_000_000_000,  # 100 Billion spent
        fiscal_year="1403"
    )
    
    # Row C: Another Region 1 row with different budget code
    row_c = BudgetRow(
        activity_id=activity.id,
        org_unit_id=1,  # Region 1
        budget_coding="TEST_LAND_ACQ_REGION1_02",
        description="آزادسازی معابر - منطقه یک (TEST DATA)",
        approved_amount=75_000_000_000,  # 75 Billion Rials
        blocked_amount=10_000_000_000,  # 10 Billion blocked
        spent_amount=15_000_000_000,  # 15 Billion spent
        fiscal_year="1403"
    )
    
    db.add(row_a)
    db.add(row_b)
    db.add(row_c)
    
    try:
        db.commit()
        print("\n✅ SUCCESS! Inserted 3 test budget rows:")
        print("\n   Row A (Region 1):")
        print(f"      ID: {row_a.id}")
        print(f"      Budget Coding: {row_a.budget_coding}")
        print(f"      org_unit_id: {row_a.org_unit_id} (Region 1)")
        print(f"      Approved: {row_a.approved_amount:,} Rials")
        print(f"      Remaining: {row_a.remaining_balance:,} Rials")
        
        print("\n   Row B (Global HQ):")
        print(f"      ID: {row_b.id}")
        print(f"      Budget Coding: {row_b.budget_coding}")
        print(f"      org_unit_id: NULL (Global - visible to all)")
        print(f"      Approved: {row_b.approved_amount:,} Rials")
        print(f"      Remaining: {row_b.remaining_balance:,} Rials")
        
        print("\n   Row C (Region 1 - Alternative):")
        print(f"      ID: {row_c.id}")
        print(f"      Budget Coding: {row_c.budget_coding}")
        print(f"      org_unit_id: {row_c.org_unit_id} (Region 1)")
        print(f"      Approved: {row_c.approved_amount:,} Rials")
        print(f"      Remaining: {row_c.remaining_balance:,} Rials")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: Failed to insert test data: {e}")
        return False


def verify_injection(db: Session):
    """Verify the test data was inserted correctly."""
    print("\n" + "="*60)
    print("  VERIFICATION")
    print("="*60)
    
    # Find activity
    activity = find_activity_by_title_keyword(db, "تملک")
    if not activity:
        print("❌ Activity not found!")
        return
    
    # Query budget rows
    rows = db.query(BudgetRow).filter(BudgetRow.activity_id == activity.id).all()
    
    print(f"\n📊 BudgetRow count for Activity ID={activity.id}: {len(rows)}")
    
    if rows:
        print("\n📋 Budget Row Details:")
        print("-" * 100)
        print(f"{'ID':>5} | {'org_unit_id':>12} | {'Approved':>18} | {'Remaining':>18} | {'Coding':25s}")
        print("-" * 100)
        
        for row in rows:
            org_display = str(row.org_unit_id) if row.org_unit_id else "NULL (Global)"
            print(f"{row.id:>5} | {org_display:>12} | {row.approved_amount:>18,} | {row.remaining_balance:>18,} | {row.budget_coding[:25]}")
    
    # Summary for API testing
    print("\n" + "="*60)
    print("  WHAT TO TEST NOW")
    print("="*60)
    print("""
1. Login as a Region 1 user (test_user, admin, or contractor)
2. Go to the Transaction Wizard
3. Select Subsystem: "سامانه شهرسازی" (Urban Planning, ID=1)
4. Select Activity: "تملک و آزادسازی اراضی" (Land Acquisition, ID=3)
5. The Budget Step should now show 3 budget rows:
   - 2 rows for Region 1 (org_unit_id=1)
   - 1 row for Global HQ (org_unit_id=NULL, visible to all)

If the list is STILL empty, the problem is in the API filtering logic!
""")


def main():
    print("\n" + "🔧" * 30)
    print("  BUDGET TEST DATA INJECTION TOOL")
    print("🔧" * 30)
    
    db = SessionLocal()
    try:
        success = inject_test_data(db)
        if success:
            verify_injection(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
