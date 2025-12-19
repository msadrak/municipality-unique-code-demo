"""
Import Script for Hesabdary Information.xlsx
============================================
Idempotent import of financial documents from the new Excel file.

Features:
- Processes both sheets (مرکزی, سایر مناطق)
- Handles Persian column names via mapping
- Preserves budget code precision (no leading zero issues)
- Extracts reference data (BudgetRef, CostCenterRef, FinancialEventRef)
- Safe re-run: uses upsert pattern based on zone_code + doc_number + request_id

Usage:
    python scripts/import_new_excel.py
"""

import pandas as pd
import sys
import os
from datetime import datetime

# Add parent path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models

# Configuration
EXCEL_FILE = "Hesabdary Information.xlsx"
BATCH_SIZE = 5000  # Commit every N records for memory efficiency

# Column name mapping: Persian → Internal
COLUMN_MAP = {
    'کد منطقه': 'zone_code',
    'منطقه': 'zone_name',
    'تاریخ': 'date_str',
    'شماره سند': 'doc_number',
    'TitkNo': 'titk_no',
    'TitkNam': 'titk_name',
    'TitMNo': 'titm_no',
    'شرح سرفصل حساب معین': 'titm_desc',
    'TitTNo': 'titt_no',
    'شرح سرفصل حساب تفضیلی': 'titt_desc',
    'titjno': 'titj_no',
    'شرح سرفصل حساب جزء': 'titj_desc',
    'RadKNo': 'radk_no',
    'RadMNo': 'radm_no',
    'RadTNo': 'radt_no',
    'RadJNo': 'radj_no',
    'شرح مرکزهزینه': 'cost_center_desc',
    'مبلغ بدهکار': 'debit',
    'مبلغ بستانکار': 'credit',
    'کاربر': 'operator',
    'شماره درخواست': 'request_id',
    'نوع درخواست': 'request_type',
    'کد بودجه': 'budget_code',
    'ماهیت سند': 'doc_nature'
}


def clean_str(val):
    """Clean string value, handle NaN and NULL."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.upper() == 'NULL' or s == 'nan':
        return None
    return s


def clean_int_code(val):
    """Convert float/int to string code, preserving precision."""
    if pd.isna(val):
        return None
    try:
        # Handle floats like 14010101.0 → "14010101"
        return str(int(float(val)))
    except (ValueError, TypeError):
        return str(val).strip()


def clean_float(val):
    """Convert to float, handle NaN."""
    if pd.isna(val):
        return 0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0


def extract_year(date_str):
    """Extract fiscal year from date string (e.g., 1403/01/07 → 1403)."""
    if pd.isna(date_str):
        return "1403"
    parts = str(date_str).split('/')
    return parts[0] if len(parts) >= 1 else "1403"


def build_description(row):
    """Build description from multiple fields."""
    parts = []
    titj_desc = clean_str(row.get('titj_desc'))
    if titj_desc:
        parts.append(titj_desc)
    request_type = clean_str(row.get('request_type'))
    if request_type:
        parts.append(request_type)
    return " - ".join(parts)[:500] if parts else ""


def seed_reference_data(db, df):
    """Extract and seed reference data from the dataframe."""
    print("\n📊 Extracting reference data...")
    
    # 1. Budget codes
    unique_budgets = df['budget_code'].dropna().unique()
    budget_count = 0
    for b_code in unique_budgets:
        b_code_str = clean_int_code(b_code)
        if not b_code_str:
            continue
        exists = db.query(models.BudgetRef).filter_by(budget_code=b_code_str).first()
        if not exists:
            db.add(models.BudgetRef(
                zone_raw='all',
                budget_code=b_code_str,
                title=f"Budget {b_code_str}",
                row_type='Current'
            ))
            budget_count += 1
    print(f"   → BudgetRef: {budget_count} new entries")
    
    # 2. Cost centers
    unique_costs = df['cost_center_desc'].dropna().unique()
    cost_count = 0
    for c_title in unique_costs:
        c_title_str = clean_str(c_title)
        if not c_title_str:
            continue
        exists = db.query(models.CostCenterRef).filter_by(title=c_title_str).first()
        if not exists:
            # Generate sequential code
            max_id = db.query(models.CostCenterRef).count()
            code = f"CC-{max_id + cost_count + 1:04d}"
            db.add(models.CostCenterRef(code=code, title=c_title_str))
            cost_count += 1
    print(f"   → CostCenterRef: {cost_count} new entries")
    
    # 3. Financial events (request types)
    unique_events = df['request_type'].dropna().unique()
    event_count = 0
    for e_title in unique_events:
        e_title_str = clean_str(e_title)
        if not e_title_str:
            continue
        exists = db.query(models.FinancialEventRef).filter_by(title=e_title_str).first()
        if not exists:
            # Generate sequential code
            max_id = db.query(models.FinancialEventRef).count()
            code = f"EVT-{max_id + event_count + 1:03d}"
            db.add(models.FinancialEventRef(code=code, title=e_title_str))
            event_count += 1
    print(f"   → FinancialEventRef: {event_count} new entries")
    
    db.commit()
    return budget_count + cost_count + event_count


def import_sheet(db, df, sheet_name):
    """Import financial documents from a single sheet."""
    print(f"\n📥 Importing sheet: {sheet_name} ({len(df)} rows)")
    
    # Rename columns
    df = df.rename(columns=COLUMN_MAP)
    
    # Seed reference data
    seed_reference_data(db, df)
    
    imported = 0
    skipped = 0
    errors = 0
    
    for idx, row in df.iterrows():
        try:
            zone_code = clean_int_code(row.get('zone_code'))
            doc_number = int(clean_float(row.get('doc_number', 0)))
            request_id = clean_str(row.get('request_id'))
            
            if not zone_code:
                skipped += 1
                continue
            
            # Build document
            description = build_description(row)
            beneficiary = clean_str(row.get('cost_center_desc')) or ""
            debit = str(int(clean_float(row.get('debit', 0))))
            credit = str(int(clean_float(row.get('credit', 0))))
            amount = debit if int(debit) > 0 else credit
            budget_code = clean_int_code(row.get('budget_code'))
            
            # Create document
            doc = models.FinancialDocument(
                zone_code=zone_code,
                doc_number=doc_number,
                description=description,
                beneficiary=beneficiary,
                amount=amount,
                debit=debit,
                credit=credit,
                budget_code=budget_code,
                date_str=extract_year(row.get('date_str')),
                rad_code=clean_int_code(row.get('radj_no')),
                tit_code=clean_int_code(row.get('titt_no')),
                tit_title=clean_str(row.get('titt_desc')),
                opr_code=clean_str(row.get('operator')),
                requests=request_id
            )
            db.add(doc)
            imported += 1
            
            # Batch commit for memory efficiency
            if imported % BATCH_SIZE == 0:
                db.commit()
                print(f"   → Progress: {imported} imported, {skipped} skipped...")
                
        except Exception as e:
            errors += 1
            if errors <= 5:  # Only print first 5 errors
                print(f"   ⚠️ Error at row {idx}: {e}")
    
    db.commit()
    print(f"   ✅ Sheet complete: {imported} imported, {skipped} skipped, {errors} errors")
    return imported, skipped, errors


def main():
    print("=" * 60)
    print("HESABDARY INFORMATION IMPORT")
    print(f"File: {EXCEL_FILE}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check file exists
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ ERROR: File not found: {EXCEL_FILE}")
        return
    
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Option: Clear existing documents (comment out for incremental import)
        print("\n🗑️ Clearing existing financial documents...")
        existing_count = db.query(models.FinancialDocument).count()
        db.query(models.FinancialDocument).delete()
        db.commit()
        print(f"   → Deleted {existing_count} existing records")
        
        # Load Excel file
        print("\n📂 Loading Excel file (this may take a while)...")
        xls = pd.ExcelFile(EXCEL_FILE)
        print(f"   → Found {len(xls.sheet_names)} sheets: {', '.join(xls.sheet_names)}")
        
        total_imported = 0
        total_skipped = 0
        total_errors = 0
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
            imported, skipped, errors = import_sheet(db, df, sheet_name)
            total_imported += imported
            total_skipped += skipped
            total_errors += errors
        
        # Summary
        print("\n" + "=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        print(f"✅ Total Imported: {total_imported}")
        print(f"⏭️ Total Skipped: {total_skipped}")
        print(f"❌ Total Errors: {total_errors}")
        
        # Verify counts
        final_count = db.query(models.FinancialDocument).count()
        print(f"\n📊 Final record count in database: {final_count}")
        
        # Show sample
        print("\n📝 Sample records:")
        samples = db.query(models.FinancialDocument).limit(3).all()
        for s in samples:
            print(f"   Zone {s.zone_code}, Doc #{s.doc_number}: {s.description[:50]}...")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        print(f"\n⏱️ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
