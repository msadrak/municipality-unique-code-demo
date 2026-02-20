import sys
import os

# Add the project root to sys.path to allow importing from 'app'
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app import models
from app.auth_utils import hash_password

def seed():
    print("Starting database seeding...")
    db = SessionLocal()
    
    # Check if we already have users
    if db.query(models.User).count() > 0:
        print("Database already has users. Skipping seeding.")
        db.close()
        return

    try:
        # 1. Create Org Units
        print("Creating organizational units...")
        zone1 = models.OrgUnit(title="منطقه ۱", code="01", org_type="ZONE")
        zone2 = models.OrgUnit(title="منطقه ۲", code="02", org_type="ZONE")
        db.add_all([zone1, zone2])
        db.commit()
        db.refresh(zone1)
        db.refresh(zone2)

        dept1 = models.OrgUnit(title="اداره مالی", code="10", parent_id=zone1.id, org_type="DEPT")
        db.add(dept1)
        db.commit()
        db.refresh(dept1)

        section1 = models.OrgUnit(title="قسمت حسابداری", code="101", parent_id=dept1.id, org_type="SECTION")
        db.add(section1)
        db.commit()
        db.refresh(section1)

        # 2. Create Users
        print("Creating default users...")
        admin = models.User(
            username="admin",
            password_hash=hash_password("admin"),
            full_name="مدیر سیستم",
            role="admin",
            admin_level=4,
            default_zone_id=zone1.id,
            is_active=True
        )
        
        user = models.User(
            username="user",
            password_hash=hash_password("user"),
            full_name="کاربر نمونه",
            role="user",
            default_zone_id=zone1.id,
            default_dept_id=dept1.id,
            default_section_id=section1.id,
            is_active=True
        )
        
        db.add_all([admin, user])

        # 3. Create Budget Items
        print("Creating sample budget items...")
        budget1 = models.BudgetItem(
            budget_code="11020401",
            description="حقوق و مزایای مستمر کارکنان",
            budget_type="expense",
            zone="منطقه ۱",
            zone_code="01",
            trustee="معاونت مالی",
            subject="پرسنلی",
            approved_1403=5000000000,
            remaining_budget=5000000000
        )
        
        budget2 = models.BudgetItem(
            budget_code="21030501",
            description="تملک دارایی - احداث پارک",
            budget_type="capital",
            zone="منطقه ۱",
            zone_code="01",
            trustee="معاونت عمران",
            subject="عمرانی",
            approved_1403=15000000000,
            remaining_budget=15000000000
        )
        
        db.add_all([budget1, budget2])

        # 4. Create Subsystems and Activities
        print("Creating subsystems and activities...")
        sub1 = models.Subsystem(code="PAYROLL", title="حقوق و دستمزد", icon="Users")
        sub2 = models.Subsystem(code="CONTRACTS", title="قراردادها", icon="FileText")
        db.add_all([sub1, sub2])
        db.commit()
        db.refresh(sub1)
        db.refresh(sub2)

        act1 = models.SubsystemActivity(
            subsystem_id=sub1.id,
            code="SALARY_PAYMENT",
            title="پرداخت حقوق ماهیانه",
            form_type="CurrentExpenseForm"
        )
        act2 = models.SubsystemActivity(
            subsystem_id=sub2.id,
            code="CONTRACT_PROGRESS",
            title="ثبت صورت وضعیت قرارداد",
            form_type="ContractorProgressForm"
        )
        db.add_all([act1, act2])

        # 5. Create Financial Events
        print("Creating financial events...")
        event1 = models.FinancialEventRef(code="101", title="پرداخت علی‌الحساب")
        event2 = models.FinancialEventRef(code="102", title="تسویه قطعی")
        db.add_all([event1, event2])

        # 6. Create Continuous Actions
        print("Creating continuous actions...")
        ca1 = models.ContinuousAction(code="CA001", title="هزینه‌های عمومی")
        ca2 = models.ContinuousAction(code="CA002", title="هزینه‌های اختصاصی")
        db.add_all([ca1, ca2])

        db.commit()
        print("Seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
