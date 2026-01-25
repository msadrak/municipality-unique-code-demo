"""
Import Region 14 Budget Items into the System
==============================================
This script imports civil works budget items from Region 14's
custom Excel file and creates activity mappings.
"""
import os
import sys
import pandas as pd
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
import argparse
from app.database import SessionLocal, engine
from app import models

# Create tables if not exist
models.Base.metadata.create_all(bind=engine)

# Constants
EXCEL_FILE = Path(__file__).parent.parent / "data" / "reports" / "Sarmayei_Region14.xlsx"
REGION_CODE = "14"
REGION_NAME = "منطقه چهارده"

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
    s = str(val).strip()
    return s if s else None

def get_or_create_org_unit(db: Session, title: str, org_type: str = "DEPUTY") -> int:
    """Get or create an organizational unit by title."""
    if not title:
        return None
    
    # Normalize the title
    title = title.strip()
    
    # Check existing
    existing = db.query(models.OrgUnit).filter(
        models.OrgUnit.title == title
    ).first()
    
    if existing:
        return existing.id
    
    # Create new OrgUnit
    new_unit = models.OrgUnit(
        title=title,
        org_type=org_type
    )
    db.add(new_unit)
    db.flush()  # Get the ID
    print(f"  [NEW] Created OrgUnit: {title} (ID: {new_unit.id})")
    return new_unit.id

def analyze_categories(df: pd.DataFrame) -> dict:
    """Analyze and return unique categories in the data."""
    categories = {
        'موضوع': df['موضوع'].dropna().unique().tolist(),
        'زیر موضوع': df['زیر موضوع'].dropna().unique().tolist(),
        'متولی': df['متولی'].dropna().unique().tolist(),
        'برنامه': df['برنامه'].dropna().unique().tolist(),
        'طرح': df['طرح'].dropna().unique().tolist(),
        'نوع ردیف': df['نوع ردیف'].dropna().unique().tolist(),
    }
    return categories

def import_region14_items(db: Session, df: pd.DataFrame) -> dict:
    """Import Region 14 budget items to database."""
    
    stats = {
        'imported': 0,
        'updated': 0,
        'skipped': 0,
        'errors': []
    }
    
    for idx, row in df.iterrows():
        try:
            budget_code = clean_str(row.get('کد بودجه'))
            if not budget_code:
                stats['skipped'] += 1
                continue
            
            # Check if already exists
            existing = db.query(models.BudgetItem).filter(
                models.BudgetItem.budget_code == budget_code
            ).first()
            
            # Get or create trustee OrgUnit
            trustee_title = clean_str(row.get('متولی'))
            trustee_id = get_or_create_org_unit(db, trustee_title) if trustee_title else None
            
            if existing:
                # Update existing item with Region 14 data
                existing.zone = clean_str(row.get('منطقه'))
                existing.subject = clean_str(row.get('موضوع'))
                existing.sub_subject = clean_str(row.get('زیر موضوع'))
                existing.trustee = trustee_title
                existing.trustee_section_id = trustee_id
                stats['updated'] += 1
            else:
                # Create new item - use only fields that exist in BudgetItem model
                item = models.BudgetItem(
                    budget_code=budget_code,
                    description=clean_str(row.get('شرح ردیف')),  # شرح ردیف is description
                    budget_type="capital",  # سرمایه‌ای = capital
                    zone=clean_str(row.get('منطقه')),
                    zone_code=REGION_CODE,  # Set zone code for Region 14
                    trustee=trustee_title,
                    trustee_section_id=trustee_id,
                    subject=clean_str(row.get('موضوع')),
                    sub_subject=clean_str(row.get('زیر موضوع')),
                    row_type=clean_str(row.get('نوع ردیف')) or "مستمر",
                    approved_1403=clean_float(row.get('مصوب 1403')),
                    allocated_1403=clean_float(row.get('تخصیص 1403')),
                    spent_1403=clean_float(row.get('هزینه 1403')),
                )
                db.add(item)
                stats['imported'] += 1
                
        except Exception as e:
            stats['errors'].append(f"Row {idx}: {str(e)}")
    
    db.commit()
    return stats

def generate_activity_mapping(categories: dict, output_path: Path):
    """Generate activity mapping CSV for review."""
    
    # Create mapping data
    rows = []
    
    # Add موضوع mappings
    for topic in categories['موضوع']:
        rows.append({
            'source_type': 'موضوع',
            'source_value': topic,
            'mapped_activity_code': '',
            'mapped_activity_name': '',
            'notes': ''
        })
    
    # Add زیر موضوع mappings
    for sub in categories['زیر موضوع']:
        rows.append({
            'source_type': 'زیر موضوع',
            'source_value': sub,
            'mapped_activity_code': '',
            'mapped_activity_name': '',
            'notes': ''
        })
    
    df = pd.DataFrame(rows)
    csv_path = output_path / 'region14_activity_mapping.csv'
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n[OUTPUT] Activity mapping template saved to: {csv_path}")
    return csv_path


def find_or_create_activity(db: Session, activity_name: str, subsystem_code: str = None):
    """Find SubsystemActivity by title, or create a new Subsystem and SubsystemActivity.

    Returns the SubsystemActivity.id
    """
    name = activity_name.strip() if activity_name else None
    if not name:
        return None

    # Try to find existing activity by exact title
    existing = db.query(models.SubsystemActivity).filter(models.SubsystemActivity.title == name).first()
    if existing:
        return existing.id

    # Find or create a generic Subsystem (e.g., 'INFRASTRUCTURE') if none provided
    subsystem = None
    if subsystem_code:
        subsystem = db.query(models.Subsystem).filter(models.Subsystem.code == subsystem_code).first()
    if not subsystem:
        subsystem = db.query(models.Subsystem).filter(models.Subsystem.code == 'INFRA').first()
    if not subsystem:
        # create a generic subsystem
        subsystem = models.Subsystem(code='INFRA', title='Infrastructure')
        db.add(subsystem)
        db.flush()

    act = models.SubsystemActivity(
        subsystem_id=subsystem.id,
        code=(name[:40]).upper().replace(' ', '_'),
        title=name,
        is_active=True
    )
    db.add(act)
    db.flush()
    print(f"  [NEW] Created SubsystemActivity: {act.title} (ID: {act.id})")
    return act.id


def create_budget_row_for_mapping(db: Session, budget_code: str, activity_id: int, approved_amount: float, zone_org_unit_id: int = None):
    """Create a BudgetRow (if not exists) linking budget_code to an activity.

    approved_amount is expected in (currency) units; convert to Rials as integer (x1)
    """
    if not budget_code or not activity_id:
        return None

    # Normalize budget_coding key
    coding = str(budget_code).strip()
    existing = db.query(models.BudgetRow).filter(models.BudgetRow.budget_coding == coding).first()
    if existing:
        return existing.id

    approved = int(approved_amount) if approved_amount and not pd.isna(approved_amount) else 0
    br = models.BudgetRow(
        activity_id=activity_id,
        org_unit_id=zone_org_unit_id,
        budget_coding=coding,
        description=f'Imported mapping for {coding}',
        approved_amount=approved,
        blocked_amount=0,
        spent_amount=0,
        fiscal_year='1403'
    )
    db.add(br)
    db.flush()
    print(f"  [NEW] Created BudgetRow for budget {coding} -> activity {activity_id} (ID: {br.id})")
    return br.id

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply-mapping', action='store_true', help='Apply mapping CSV to create activities and budget rows')
    parser.add_argument('--mapping-file', type=str, default=None, help='Path to mapping CSV (prefill)')
    parser.add_argument('--dry-run', action='store_true', help='Do not commit DB changes')
    args = parser.parse_args()
    print("=" * 60)
    print("Region 14 Budget Import Script")
    print("=" * 60)
    
    # Verify file exists
    if not EXCEL_FILE.exists():
        print(f"ERROR: File not found: {EXCEL_FILE}")
        return
    
    # Load data
    print(f"\n[1] Loading: {EXCEL_FILE.name}")
    df = pd.read_excel(EXCEL_FILE)
    print(f"    Rows: {len(df)}, Columns: {len(df.columns)}")
    
    # Analyze categories
    print("\n[2] Analyzing categories...")
    categories = analyze_categories(df)
    
    print(f"\n    موضوع (Topics): {len(categories['موضوع'])}")
    for t in categories['موضوع'][:10]:
        print(f"      - {t}")
    if len(categories['موضوع']) > 10:
        print(f"      ... and {len(categories['موضوع']) - 10} more")
    
    print(f"\n    متولی (Trustees): {len(categories['متولی'])}")
    for t in categories['متولی']:
        print(f"      - {t}")
    
    print(f"\n    نوع ردیف (Row Types): {categories['نوع ردیف']}")
    
    # Generate activity mapping template
    print("\n[3] Generating activity mapping template...")
    output_dir = Path(__file__).parent
    generate_activity_mapping(categories, output_dir)
    
    # Import to database
    print("\n[4] Importing to database...")
    db = SessionLocal()
    
    try:
        stats = import_region14_items(db, df)
        
        print("\n" + "=" * 60)
        print("IMPORT SUMMARY")
        print("=" * 60)
        print(f"  New items imported: {stats['imported']}")
        print(f"  Existing items updated: {stats['updated']}")
        print(f"  Skipped: {stats['skipped']}")
        if stats['errors']:
            print(f"  Errors: {len(stats['errors'])}")
            for e in stats['errors'][:5]:
                print(f"    - {e}")
        
        # Verification
        total = db.query(models.BudgetItem).filter(
            models.BudgetItem.zone.like(f'{REGION_CODE}%')
        ).count()
        print(f"\n  Total Region 14 items in DB: {total}")

        # Optionally apply mapping CSV
        if args.apply_mapping:
            mapping_path = Path(args.mapping_file) if args.mapping_file else Path(__file__).parent / 'region14_activity_mapping_prefill.csv'
            if not mapping_path.exists():
                print(f"Mapping file not found: {mapping_path}")
            else:
                print(f"\n[5] Applying mappings from: {mapping_path}")
                map_df = pd.read_csv(mapping_path)
                applied = 0
                for _, mrow in map_df.iterrows():
                    mapped_name = clean_str(mrow.get('mapped_activity_name')) or clean_str(mrow.get('suggested_activity_name')) or ''
                    mapped_code = clean_str(mrow.get('mapped_activity_code'))
                    budget_code = clean_str(mrow.get('budget_code')) or clean_str(mrow.get('source_value'))
                    # Lookup BudgetItem
                    bitem = db.query(models.BudgetItem).filter(models.BudgetItem.budget_code == budget_code).first()
                    if not bitem:
                        # Skip if budget item not imported
                        print(f"  [SKIP] BudgetItem not found for code: {budget_code}")
                        continue

                    # Create/find activity
                    activity_id = None
                    if mapped_name:
                        activity_id = find_or_create_activity(db, mapped_name)

                    # If we have activity, create a BudgetRow (if not exists)
                    if activity_id:
                        # find org_unit id by trustee section if available
                        zone_org_unit_id = None
                        if bitem.trustee_section_id:
                            zone_org_unit_id = bitem.trustee_section_id
                        create_budget_row_for_mapping(db, bitem.budget_code, activity_id, bitem.approved_1403 or 0, zone_org_unit_id)
                        applied += 1

                print(f"Applied mappings (created activities/budget rows): {applied}")
                if args.dry_run:
                    print("Dry-run: rolling back changes")
                    db.rollback()
                else:
                    db.commit()
        
    finally:
        db.close()
    
    print("\n[DONE] Import completed successfully!")

if __name__ == "__main__":
    main()
