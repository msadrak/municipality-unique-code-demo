import sys
import os

# اضافه کردن مسیر اصلی پروژه به پایتون برای شناختن ماژول‌ها
sys.path.append(os.getcwd())

from sqlalchemy import func
from app.database import SessionLocal
from app import models

def audit_database():
    db = SessionLocal()
    print("\n" + "="*50)
    print("📊 DATABASE HEALTH & STATUS REPORT")
    print("="*50 + "\n")

    # 1. Subsystems (سامانه‌ها)
    sub_count = db.query(models.Subsystem).count()
    print(f"✅ Subsystems (سامانه‌ها): {sub_count}")
    if sub_count > 0:
        subs = db.query(models.Subsystem).all()
        for s in subs:
            act_count = db.query(models.SubsystemActivity).filter_by(subsystem_id=s.id).count()
            print(f"   - {s.title} ({s.code}): {act_count} Activities")

    # 2. Activities & Constraints (فعالیت‌ها و قوانین)
    print("\n🔍 Activity Configuration Check:")
    activities = db.query(models.SubsystemActivity).all()
    no_constraint_count = 0
    for act in activities:
        cons_count = db.query(models.ActivityConstraint).filter_by(subsystem_activity_id=act.id).count()
        if cons_count == 0:
            no_constraint_count += 1
            print(f"   ⚠️  WARNING: Activity '{act.title}' has NO constraints defined.")
    
    if no_constraint_count == 0:
        print("   ✅ All activities have configured constraints.")

    # 3. Master Data (داده‌های مرجع - اکسل‌ها)
    print("\n📚 Master Data Stats (Layer 1):")
    
    # Budget Items
    budget_count = db.query(models.BudgetRef).count()
    print(f"   - Budget Rows (ردیف‌های بودجه): {budget_count}")
    if budget_count == 0:
        print("     🔴 CRITICAL: Budget table is empty! Run import_budget script.")

    # Org Units
    org_count = db.query(models.OrgUnit).count()
    print(f"   - Org Units (واحد‌های سازمانی): {org_count}")
    
    # Cost Centers
    try:
        # فرض می‌کنیم مدل CostCenter دارید (اگر ندارید این بخش خطا ندهد)
        cc_count = db.query(models.CostCenterRef).count()
        print(f"   - Cost Centers (مراکز هزینه): {cc_count}")
        if cc_count == 0:
            print("     🟠 Action Required: Cost Centers are missing.")
    except:
        print("   - Cost Centers table: Not found or defined yet.")

    # Continuous Actions
    try:
        ca_count = db.query(models.ContinuousActionRef).count()
        print(f"   - Continuous Actions (اقدامات مستمر): {ca_count}")
        if ca_count == 0:
            print("     🟠 Action Required: Continuous Actions are missing.")
    except:
        print("   - Continuous Actions table: Not found or defined yet.")

    print("\n" + "="*50)
    db.close()

if __name__ == "__main__":
    audit_database()