import sys
import os
import random
from decimal import Decimal
from sqlalchemy.orm import Session

# Reconfigure stdout for UTF-8 to handle Persian/emojis on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for older python versions if needed
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Add project root to sys.path for app imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, engine
from app.models.attendance import (
    WorkPeriod, RegionalAttendanceSheet, AttendanceRecord,
    ContractorStatement, ContractorStatementItem
)
from app.models.users import User
from app.models.enums import AttendanceSheetStatus, WorkFlowStatus, UserRole
from app.utils.pricing_engine import calculate_record_legal_value
from app.utils.constants import AUTHORIZED_REGIONS

# Realistic Persian Data Buckets
FIRST_NAMES = ["علی", "رضا", "محمد", "حسین", "مهدی", "حمید", "جواد", "مصطفی", "اکبر", "اصغر", "روح‌الله", "سجاد", "سعید", "امیر", "بابک", "پیمان", "رامین", "شایان", "فرهاد", "کوروش"]
LAST_NAMES = ["احمدی", "رضایی", "حسینی", "محمدی", "کشاورز", "مرادی", "کریمی", "نادری", "تیموری", "باقری", "صادقی", "هاشمی", "موسوی", "علیزاده", "حیدری", "قاسمی", "اکبری", "نیکو", "فلاح", "روشنایی"]
FATHER_NAMES = ["حسن", "مرتضی", "ابراهیم", "قاسم", "صفر", "کرم", "نعمت", "پرویز"]

def generate_national_id():
    return "".join([str(random.randint(0, 9)) for _ in range(10)])

def generate_random_personnel(num=1, profile="random"):
    personnel = []
    for _ in range(num):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        marital = random.choice(["متأهل", "مجرد"])
        children = random.randint(0, 3) if marital == "متأهل" else 0
        
        # Base days
        days = Decimal(str(random.randint(25, 31)))
        ot_hours = Decimal("0")
        
        if profile == "clean":
            days = Decimal("30")
            ot_hours = Decimal("0")
        elif profile == "ot_heavy":
            ot_hours = Decimal(str(random.randint(45, 50)))
        elif profile == "variable":
            days = Decimal(str(random.randint(20, 31)))
            ot_hours = Decimal(str(random.randint(5, 60)))
        else: # random
            days = Decimal(str(random.randint(22, 31)))
            ot_hours = Decimal(str(random.randint(0, 40)))
            
        personnel.append({
            "full_name": f"{first} {last}",
            "father_name": random.choice(FATHER_NAMES),
            "national_id": generate_national_id(),
            "marital_status": marital,
            "children_count": children,
            "monthly_performance_days": days,
            "total_overtime_given": ot_hours,
            "holiday_work_days": random.randint(0, 4),
            "friday_work_days": random.randint(0, 4),
            "shift_22_5_days": random.randint(0, 5) if profile == "variable" else 0
        })
    return personnel

def seed_demo_data():
    db = SessionLocal()
    YEAR = 1405
    MONTH = 1
    
    print(f"--- 🚀 Seeding Demo Data for {YEAR}/{MONTH} ---")
    
    try:
        # 0. Safety: Cleanup existing 1405/1 data
        print("Cleaning up old 1405/1 data...")
        existing_wp = db.query(WorkPeriod).filter(WorkPeriod.year == YEAR, WorkPeriod.month == MONTH).first()
        if existing_wp:
            db.delete(existing_wp)
            db.commit()
            print("  ✓ Old data purged.")

        # 1. Create WorkPeriod
        work_period = WorkPeriod(
            year=YEAR,
            month=MONTH,
            status=WorkFlowStatus.PENDING_SECURITY_AUDIT,
            total_regions_uploaded=5
        )
        db.add(work_period)
        db.flush()
        
        # 2. Pick 5 Regions from constants
        # To make it deterministic for the demo, we pick specific ones if they exist or just random 5
        selected_regions = random.sample(AUTHORIZED_REGIONS, 5)
        
        # 3. Fetch Users
        # We need regional users (Stage 1/2 creators) and the contractor user
        contractor_user = db.query(User).filter(User.role == UserRole.CONTRACTOR).first()
        if not contractor_user:
            # Fallback if DB is empty of users
            contractor_user = User(username="contractor", role=UserRole.CONTRACTOR, full_name="پیمانکار آزمایش")
            db.add(contractor_user)
            db.flush()
            
        region_users = {}
        for region_name in selected_regions:
            u = db.query(User).filter(User.region_name == region_name).first()
            if not u:
                u = db.query(User).filter(User.username.ilike("%" + region_name[:5] + "%")).first()
            if not u:
                # Create a temporary regional user if not exists
                u = User(username=f"user_{region_name[:5]}", role=UserRole.REGION_USER, region_name=region_name, full_name=f"مسئول {region_name}")
                db.add(u)
                db.flush()
            region_users[region_name] = u

        # 4. Generate Sheets and Records
        true_grand_total = Decimal("0")
        regional_costs = {}
        record_count = 0
        
        profiles = ["clean", "ot_heavy", "variable", "random", "random"]
        
        for i, region_name in enumerate(selected_regions):
            profile = profiles[i]
            user = region_users[region_name]
            
            sheet = RegionalAttendanceSheet(
                title=f"لیست حضور و غیاب {region_name} - {YEAR}/{MONTH}",
                year=YEAR,
                month=MONTH,
                region=region_name,
                original_filename=f"attendance_{region_name}_1405_01.xlsx",
                status=AttendanceSheetStatus.GM_APPROVED,
                work_period_id=work_period.id,
                created_by_id=user.id
            )
            db.add(sheet)
            db.flush()
            
            # Generate 15-30 records
            num_records = random.randint(15, 30)
            personnel_list = generate_random_personnel(num_records, profile=profile)
            
            region_sum = Decimal("0")
            for idx, p in enumerate(personnel_list):
                record = AttendanceRecord(
                    sheet_id=sheet.id,
                    work_period_id=work_period.id,
                    row_number=idx + 1,
                    full_name=p["full_name"],
                    father_name=p["father_name"],
                    national_id=p["national_id"],
                    marital_status=p["marital_status"],
                    children_count=p["children_count"],
                    monthly_performance_days=p["monthly_performance_days"],
                    total_overtime_given=p["total_overtime_given"],
                    # Add dynamic attributes for pricing engine (even if not in DB columns)
                    # Note: These won't persist to DB unless columns exist, 
                    # but we use them for the summary calculation here.
                )
                setattr(record, "holiday_work_days", p["holiday_work_days"])
                setattr(record, "friday_work_days", p["friday_work_days"])
                setattr(record, "shift_22_5_days", p["shift_22_5_days"])
                
                db.add(record)
                
                # Calculate True Value
                val = calculate_record_legal_value(record)
                region_sum += val
                record_count += 1
                
            sheet.row_count = num_records
            regional_costs[region_name] = region_sum
            true_grand_total += region_sum
            print(f"  ✓ Region: {region_name} ({profile}) -> Records: {num_records}, Total: {region_sum:,.0f} IRR")

        # 5. Simulate Contractor Statement (Stage 3)
        # Deliberate Discrepancy: 5% overcharge
        declared_total = true_grand_total * Decimal("1.05")
        discrepancy_amount = declared_total - true_grand_total
        
        statement = ContractorStatement(
            work_period_id=work_period.id,
            year=YEAR,
            month=MONTH,
            region_name="تجمیعی کل مناطق",
            declared_total_amount=declared_total
        )
        db.add(statement)
        db.flush()
        
        # Generate 5 Summary Items
        # Item 2 (Region 2 - OT Heavy) will carry the entire delta
        target_region_for_error = selected_regions[1] # "ot_heavy" region
        
        for i, region_name in enumerate(selected_regions):
            base_amt = regional_costs[region_name]
            if region_name == target_region_for_error:
                item_amt = base_amt + discrepancy_amount
            else:
                item_amt = base_amt
                
            item = ContractorStatementItem(
                statement_id=statement.id,
                row_number=i + 1,
                full_name=f"صورت وضعیت {region_name}",
                net_payable_amount=item_amt,
                gross_amount=item_amt * Decimal("1.1"), # Dummy gross
                tax_deduction=item_amt * Decimal("0.05"),
                insurance_deduction=item_amt * Decimal("0.05")
            )
            db.add(item)
            
        db.commit()
        
        print("\n" + "="*60)
        print(f" DEMO DATA SEEDED SUCCESSFULLY")
        print("="*60)
        print(f"{'Region Name':<35} | {'True Cost (IRR)':>20}")
        print("-" * 60)
        for reg, cost in regional_costs.items():
            print(f"{reg:<35} | {cost:>20,.0f}")
        print("-" * 60)
        print(f"{'SYSTEM CALCULATED TOTAL':<35} | {true_grand_total:>20,.0f}")
        print(f"{'CONTRACTOR DECLARED TOTAL':<35} | {declared_total:>20,.0f}")
        print(f"{'DELTA (5% DISCREPANCY)':<35} | {discrepancy_amount:>20,.0f}")
        print("="*60)
        print(f"Target of Discrepancy: {target_region_for_error}")
        print("="*60)

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
