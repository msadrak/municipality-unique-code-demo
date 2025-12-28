"""Diagnose Treasury budget rows"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Subsystem, SubsystemActivity, BudgetRow, User

db = SessionLocal()

print("=" * 60)
print("TREASURY SUBSYSTEM BUDGET DIAGNOSTIC")
print("=" * 60)

# Get Treasury subsystem
treasury = db.query(Subsystem).filter(Subsystem.code == 'TREASURY').first()
print(f"\nTreasury Subsystem: ID={treasury.id}, '{treasury.title}'")

# Get Treasury activities
activities = db.query(SubsystemActivity).filter(
    SubsystemActivity.subsystem_id == treasury.id,
    SubsystemActivity.is_active == True
).all()

print(f"\nTreasury has {len(activities)} activities:")
print("-" * 60)

for act in activities:
    budget_count = db.query(BudgetRow).filter(BudgetRow.activity_id == act.id).count()
    global_count = db.query(BudgetRow).filter(
        BudgetRow.activity_id == act.id,
        BudgetRow.org_unit_id.is_(None)
    ).count()
    status = "✅" if budget_count > 0 else "❌"
    print(f"  {status} ID={act.id}: {act.title[:40]:40s} | {budget_count:3d} budgets ({global_count} global)")

# Check test_user
print("\n" + "=" * 60)
print("USER ZONE CHECK")
print("=" * 60)

test_user = db.query(User).filter(User.username == 'test_user').first()
print(f"\ntest_user:")
print(f"  default_zone_id = {test_user.default_zone_id}")
print(f"  default_section_id = {test_user.default_section_id}")

finance_user = db.query(User).filter(User.username == 'finance_test').first()
if finance_user:
    print(f"\nfinance_test:")
    print(f"  default_zone_id = {finance_user.default_zone_id}")
    print(f"  default_section_id = {finance_user.default_section_id}")

db.close()
