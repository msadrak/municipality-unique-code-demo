"""
Import script: Populate org_budget_map table from Hesabdary Information.xlsx

Extracts distinct combinations of:
- zone_code (کد منطقه)
- budget_code (کد بودجه)
- cost_center_desc (شرح مرکزهزینه)
- continuous_action_desc (شرح سرفصل حساب جزء)

Usage:
    python scripts/import_org_budget_map.py
"""

import pandas as pd
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, OrgBudgetMap

# Excel file path
EXCEL_PATH = "Hesabdary Information.xlsx"

# Column mappings (Persian → internal)
COL_ZONE_CODE = 'کد منطقه'
COL_BUDGET_CODE = 'کد بودجه'
COL_COST_CENTER = 'شرح مرکزهزینه'
COL_CONTINUOUS_ACTION = 'شرح سرفصل حساب جزء'


def normalize_value(val):
    """Clean and normalize a value."""
    if pd.isna(val):
        return None
    if isinstance(val, float):
        # Handle float -> int for codes
        if val == int(val):
            return str(int(val))
        return str(val)
    return str(val).strip() if str(val).strip() else None


def process_sheet(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """
    Process a single sheet and extract distinct mapping rows.
    """
    print(f"\n  Processing sheet: {sheet_name}")
    print(f"    Raw rows: {len(df):,}")
    
    # Check required columns exist
    required = [COL_ZONE_CODE]
    optional = [COL_BUDGET_CODE, COL_COST_CENTER, COL_CONTINUOUS_ACTION]
    
    for col in required:
        if col not in df.columns:
            print(f"    ERROR: Required column '{col}' not found!")
            return pd.DataFrame()
    
    # Extract and normalize columns
    result = pd.DataFrame()
    result['zone_code'] = df[COL_ZONE_CODE].apply(normalize_value)
    
    for col, target in [
        (COL_BUDGET_CODE, 'budget_code'),
        (COL_COST_CENTER, 'cost_center_desc'),
        (COL_CONTINUOUS_ACTION, 'continuous_action_desc')
    ]:
        if col in df.columns:
            result[target] = df[col].apply(normalize_value)
        else:
            result[target] = None
    
    # Filter out rows with no zone_code
    result = result[result['zone_code'].notna()]
    print(f"    After zone filter: {len(result):,}")
    
    # Get distinct combinations
    result = result.drop_duplicates()
    print(f"    Distinct combinations: {len(result):,}")
    
    return result


def import_to_db(mapping_df: pd.DataFrame):
    """
    Insert mapping rows into org_budget_map table.
    Uses delete-then-insert strategy for idempotency.
    """
    print("\n  Importing to database...")
    
    # Create table if not exists
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Clear existing data
        deleted = db.query(OrgBudgetMap).delete()
        print(f"    Deleted {deleted:,} existing rows")
        
        # Insert new data
        inserted = 0
        for _, row in mapping_df.iterrows():
            record = OrgBudgetMap(
                zone_code=row['zone_code'],
                budget_code=row.get('budget_code'),
                cost_center_desc=row.get('cost_center_desc'),
                continuous_action_desc=row.get('continuous_action_desc')
            )
            db.add(record)
            inserted += 1
            
            if inserted % 10000 == 0:
                db.flush()
                print(f"    Inserted {inserted:,} rows...")
        
        db.commit()
        print(f"    Total inserted: {inserted:,} rows")
        
        # Verify counts
        total = db.query(OrgBudgetMap).count()
        zones = db.query(OrgBudgetMap.zone_code).distinct().count()
        budgets = db.query(OrgBudgetMap.budget_code).filter(OrgBudgetMap.budget_code.isnot(None)).distinct().count()
        cost_centers = db.query(OrgBudgetMap.cost_center_desc).filter(OrgBudgetMap.cost_center_desc.isnot(None)).distinct().count()
        cont_actions = db.query(OrgBudgetMap.continuous_action_desc).filter(OrgBudgetMap.continuous_action_desc.isnot(None)).distinct().count()
        
        print(f"\n  Verification:")
        print(f"    Total records: {total:,}")
        print(f"    Distinct zones: {zones}")
        print(f"    Distinct budget codes: {budgets:,}")
        print(f"    Distinct cost centers: {cost_centers:,}")
        print(f"    Distinct continuous actions: {cont_actions:,}")
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def main():
    print("=" * 60)
    print("OrgBudgetMap Import Script")
    print("=" * 60)
    
    # Check file exists
    if not os.path.exists(EXCEL_PATH):
        print(f"ERROR: File not found: {EXCEL_PATH}")
        print("Make sure Hesabdary Information.xlsx is in the current directory.")
        return
    
    print(f"\nReading: {EXCEL_PATH}")
    
    # Read both sheets
    all_mappings = []
    
    try:
        # Sheet 1: مرکزی
        df1 = pd.read_excel(EXCEL_PATH, sheet_name='مرکزی')
        mappings1 = process_sheet(df1, 'مرکزی')
        all_mappings.append(mappings1)
    except Exception as e:
        print(f"  Warning: Could not read 'مرکزی' sheet: {e}")
    
    try:
        # Sheet 2: سایر مناطق
        df2 = pd.read_excel(EXCEL_PATH, sheet_name='سایر مناطق')
        mappings2 = process_sheet(df2, 'سایر مناطق')
        all_mappings.append(mappings2)
    except Exception as e:
        print(f"  Warning: Could not read 'سایر مناطق' sheet: {e}")
    
    if not all_mappings:
        print("ERROR: No data extracted from any sheet!")
        return
    
    # Combine and deduplicate
    combined = pd.concat(all_mappings, ignore_index=True)
    combined = combined.drop_duplicates()
    print(f"\n  Combined distinct mappings: {len(combined):,}")
    
    # Import to database
    import_to_db(combined)
    
    print("\n" + "=" * 60)
    print("Import complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
