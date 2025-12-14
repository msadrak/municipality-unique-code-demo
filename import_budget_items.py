"""
Import script for budget items from two Excel files:
- اعتبارات هزینه ای.xlsx (Cost budgets - all مستمر)
- تملک دارایی سرمایه ای.xlsx (Capital budgets - مستمر/غیرمستمر)
"""
import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

# Create tables
models.Base.metadata.create_all(bind=engine)

def clean_float(val):
    """Convert to float, handle NaN"""
    if pd.isna(val):
        return None
    try:
        return float(val)
    except:
        return None

def clean_str(val):
    """Clean string values"""
    if pd.isna(val):
        return None
    return str(val).strip()

def import_hazine(db: Session, seen_codes: set):
    """Import اعتبارات هزینه ای.xlsx"""
    print("Loading اعتبارات هزینه ای.xlsx...")
    df = pd.read_excel("اعتبارات هزینه ای.xlsx")
    
    count = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        budget_code = clean_str(row.get('کد بودجه'))
        if not budget_code:
            skipped += 1
            continue
        
        # Check if already seen (in memory)
        if budget_code in seen_codes:
            skipped += 1
            continue
            
        # Check if already exists in DB
        existing = db.query(models.BudgetItem).filter(
            models.BudgetItem.budget_code == budget_code
        ).first()
        
        if existing:
            seen_codes.add(budget_code)
            skipped += 1
            continue
        
        item = models.BudgetItem(
            budget_code=budget_code,
            description=clean_str(row.get('شرح ردیف')),
            budget_type="hazine",
            zone=None,  # Will be inferred from trustee
            trustee=clean_str(row.get('متولی')),
            subject=clean_str(row.get('موضوع')),
            sub_subject=None,
            row_type="مستمر",  # All hazine are مستمر
            approved_1403=clean_float(row.get('مصوب 1403')),
            allocated_1403=clean_float(row.get('تخصیص 1403')),
            spent_1403=clean_float(row.get('هزینه 1403'))
        )
        db.add(item)
        seen_codes.add(budget_code)
        count += 1
    
    db.commit()
    print(f"  Imported {count} hazine items, skipped {skipped}")
    return count

def import_sarmaye(db: Session, seen_codes: set):
    """Import تملک دارایی سرمایه ای.xlsx"""
    print("Loading تملک دارایی سرمایه ای.xlsx...")
    df = pd.read_excel("تملک دارایی سرمایه ای.xlsx")
    
    count = 0
    skipped = 0
    updated = 0
    
    for idx, row in df.iterrows():
        budget_code = clean_str(row.get('کد بودجه'))
        if not budget_code:
            skipped += 1
            continue
        
        # Check if already seen (in memory - handles duplicates in file)
        if budget_code in seen_codes:
            skipped += 1
            continue
        
        # Check if already exists in DB (from hazine)
        existing = db.query(models.BudgetItem).filter(
            models.BudgetItem.budget_code == budget_code
        ).first()
        
        if existing:
            # Update with sarmaye info if missing
            if not existing.zone and clean_str(row.get('منطقه')):
                existing.zone = clean_str(row.get('منطقه'))
                updated += 1
            seen_codes.add(budget_code)
            skipped += 1
            continue
        
        item = models.BudgetItem(
            budget_code=budget_code,
            description=clean_str(row.get('شرح ردیف')),
            budget_type="sarmaye",
            zone=clean_str(row.get('منطقه')),
            trustee=clean_str(row.get('متولی')),
            subject=clean_str(row.get('موضوع')),
            sub_subject=clean_str(row.get('زیر موضوع')),
            row_type=clean_str(row.get('نوع ردیف')) or "مستمر",
            approved_1403=clean_float(row.get('مصوب 1403')),
            allocated_1403=clean_float(row.get('تخصیص 1403')),
            spent_1403=clean_float(row.get('هزینه 1403'))
        )
        db.add(item)
        seen_codes.add(budget_code)
        count += 1
    
    db.commit()
    print(f"  Imported {count} sarmaye items, skipped {skipped}, updated {updated}")
    return count

def main():
    print("=" * 50)
    print("Budget Items Import Script")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # Clear existing data
        print("\nClearing existing budget_items...")
        db.query(models.BudgetItem).delete()
        db.commit()
        
        # Track seen codes to handle duplicates
        seen_codes = set()
        
        # Import both files
        hazine_count = import_hazine(db, seen_codes)
        sarmaye_count = import_sarmaye(db, seen_codes)
        
        # Summary
        total = db.query(models.BudgetItem).count()
        print("\n" + "=" * 50)
        print(f"TOTAL: {total} budget items imported")
        print("=" * 50)
        
        # Show sample
        print("\nSample items:")
        samples = db.query(models.BudgetItem).limit(5).all()
        for s in samples:
            print(f"  {s.budget_code}: {s.description[:40] if s.description else 'N/A'}... ({s.budget_type})")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
