import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the Python path
sys.path.append(os.getcwd())

from app.database import Base, SessionLocal
from app.models import BudgetRow, SubsystemActivity, OrgUnit

def clean_budget_coding(val):
    """Normalize budget coding (remove spaces, Persian numbers)."""
    if pd.isna(val):
        return None
    val = str(val).strip()
    return val

def parse_amount(val):
    """Parse amount, handling commas and nulls."""
    if pd.isna(val):
        return 0
    try:
        clean_val = str(val).replace(',', '').strip()
        if not clean_val:
            return 0
        return int(float(clean_val))
    except (ValueError, TypeError):
        return 0

def get_zone_id(zone_str):
    """
    Strict mapping of Zone string to OrgUnit ID.
    'منطقه ۱', 'منطقه 1' -> 1
    'مرکز', 'ستاد' -> None (Global)
    'منطقه 2' -> 2, etc. (Not needed for this task but good to handle)
    """
    if pd.isna(zone_str):
        return None # Global/HQ if not specified? Or should we default to HQ?
    
    zone_str = str(zone_str).strip()
    
    # Explicit Mapping for Zone 1
    if 'منطقه 1' in zone_str or 'منطقه ۱' in zone_str:
        return 1
    
    # Handle 'Markaz' / HQ
    if 'مرکز' in zone_str or 'ستاد' in zone_str or 'ناژوان' in zone_str:
        return None # Global
    
    # Default to None if not matched (Safest for now to avoid wrong assignment)
    return None

def seed_real_budget():
    db = SessionLocal()
    try:
        print("🔧 Starting Real Budget Seeding...")
        
        # 1. Cleanup TEST Data
        # ----------------------------------------------------
        deleted = db.query(BudgetRow).filter(BudgetRow.budget_coding.like('TEST_%')).delete(synchronize_session=False)
        print(f"🗑️ Deleted {deleted} dummy test rows.")
        db.commit()

        # 2. Get Target Activity (Land Acquisition)
        # ----------------------------------------------------
        # We know ID=3, but let's find it safely
        activity = db.query(SubsystemActivity).filter(SubsystemActivity.id == 3).first()
        if not activity:
            activity = db.query(SubsystemActivity).filter(
                SubsystemActivity.title.contains("تملک"),
                SubsystemActivity.title.contains("اراضی")
            ).first()
        
        if not activity:
            print("❌ Error: Target Activity 'Land Acquisition' (ID 3) not found.")
            return
        
        print(f"✅ Target Activity: {activity.title} (ID: {activity.id})")

        # 3. Load Excel Data
        # ----------------------------------------------------
        excel_path = 'تملک دارایی سرمایه ای.xlsx'
        if not os.path.exists(excel_path):
            print(f"❌ Error: File '{excel_path}' not found.")
            return
            
        print(f"📖 Reading '{excel_path}'...")
        df = pd.read_excel(excel_path)
        
        # Verify columns based on user feedback
        required_cols = ['منطقه', 'کد بودجه', 'شرح ردیف', 'مصوب 1403']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
             print(f"❌ Error: Missing columns: {missing}")
             print(f"Found columns: {df.columns.tolist()}")
             return

        # 4. Filter & Insert Rows
        # ----------------------------------------------------
        count = 0
        skipped = 0
        
        for _, row in df.iterrows():
            desc = str(row['شرح ردیف'])
            
            # Explicit Activity Matching: "تملک" AND ("اراضی" OR "آزادسازی")
            if 'تملک' in desc and ('اراضی' in desc or 'آزادسازی' in desc):
                
                # Parse Fields
                zone_val = row['منطقه']
                org_unit_id = get_zone_id(zone_val)
                
                budget_code = clean_budget_coding(row['کد بودجه'])
                amount = parse_amount(row['مصوب 1403'])
                
                if amount <= 0:
                    continue # Skip zero amount rows

                # Check if exists (upsert logic) - GLOBALLY Unique Check
                existing = db.query(BudgetRow).filter(
                    BudgetRow.budget_coding == budget_code
                ).first()
                
                if existing:
                    # Update existing record
                    # print(f"♻️ Updating existing code: {budget_code}")
                    existing.approved_amount = amount
                    existing.org_unit_id = org_unit_id
                    existing.description = desc
                    # Ensure it belongs to the correct activity if we are sure
                    existing.activity_id = activity.id 
                else:
                    # Insert
                    new_budget = BudgetRow(
                        activity_id=activity.id,
                        org_unit_id=org_unit_id,
                        budget_coding=budget_code,
                        description=desc,
                        approved_amount=amount,
                        blocked_amount=0,
                        spent_amount=0,
                        fiscal_year="1403"
                    )
                    db.add(new_budget)
                
                count += 1
            else:
                skipped += 1
                
        db.commit()
        print(f"🎉 Success! Processed {count} matching rows.")
        print(f"ℹ️ Skipped {skipped} non-matching rows.")
        
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_real_budget()
