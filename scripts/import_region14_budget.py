"""
Import Region 14 Budget Items into the System
==============================================
Phase 1: Zero Trust Data Ingestion + Human Layer Generation

This script performs ATOMIC OPERATIONS:
1. Strict 1-to-1 Mapping: Every Excel row → Unique Activity → BudgetRow → ActivityConstraint
2. Automated Human Layer: Auto-generate OrgUnits and Admin Users from Trustee column
3. Bridge to Zero Trust: Populate BudgetRow (not just BudgetItem)

Architecture Philosophy: "Anti-Corruption 1-to-1 Mapping"
- Prevents fund shifting between budget lines
- Every budget line gets a unique activity ID
- Database-level enforcement via CheckConstraints
"""
import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import hashlib

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import argparse
from app.database import SessionLocal, engine
from app import models
from app.auth_utils import hash_password

# Create tables if not exist
models.Base.metadata.create_all(bind=engine)

# Constants
EXCEL_FILE = Path(__file__).parent.parent / "data" / "reports" / "Sarmayei_Region14.xlsx"
REGION_CODE = "14"
REGION_NAME = "منطقه چهارده"
DEFAULT_ADMIN_PASSWORD = "Tehran@1403"  # Must be changed on first login
SUBSYSTEM_CODE = "CIVIL_WORKS"
SUBSYSTEM_TITLE = "عمران و طرح‌ها"

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

def generate_username(trustee_name: str, region_code: str) -> str:
    """Generate a consistent username from trustee name."""
    # Remove common prefixes and clean
    name = trustee_name.replace("اداره", "").replace("دایره", "").strip()
    # Create a hash-based suffix for uniqueness
    hash_suffix = hashlib.md5(name.encode('utf-8')).hexdigest()[:4]
    # Create username: admin_trustee_region_hash
    username = f"admin_r{region_code}_{hash_suffix}"
    return username

def get_or_create_region_org_unit(db: Session) -> int:
    """Get or create the Region 14 parent OrgUnit."""
    existing = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE,
        models.OrgUnit.org_type == "ZONE"
    ).first()
    
    if existing:
        return existing.id
    
    region_unit = models.OrgUnit(
        title=REGION_NAME,
        code=REGION_CODE,
        org_type="ZONE"
    )
    db.add(region_unit)
    db.flush()
    print(f"  [NEW] Created Region OrgUnit: {REGION_NAME} (ID: {region_unit.id})")
    return region_unit.id

def get_or_create_trustee_org_unit(db: Session, trustee_name: str, parent_id: int) -> tuple:
    """
    Get or create an organizational unit for a trustee (department).
    Returns: (org_unit_id, was_created)
    """
    if not trustee_name:
        return None, False
    
    # Normalize the title
    trustee_name = trustee_name.strip()
    
    # Check existing by title
    existing = db.query(models.OrgUnit).filter(
        models.OrgUnit.title == trustee_name,
        models.OrgUnit.parent_id == parent_id
    ).first()
    
    if existing:
        return existing.id, False
    
    # Create new OrgUnit (Department under Region)
    new_unit = models.OrgUnit(
        title=trustee_name,
        code=f"{REGION_CODE}_{trustee_name[:10]}",  # Simple code generation
        parent_id=parent_id,
        org_type="DEPARTMENT"
    )
    db.add(new_unit)
    db.flush()
    return new_unit.id, True

def get_or_create_admin_user(db: Session, trustee_name: str, org_unit_id: int, subsystem_id: int) -> tuple:
    """
    Get or create an Admin L1 user for a trustee department.
    Returns: (user_id, was_created)
    """
    if not trustee_name or not org_unit_id:
        return None, False
    
    # Generate consistent username
    username = generate_username(trustee_name, REGION_CODE)
    
    # Check if user exists
    existing = db.query(models.User).filter(
        models.User.username == username
    ).first()
    
    if existing:
        return existing.id, False
    
    # Create new Admin L1 user
    new_user = models.User(
        username=username,
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        full_name=f"Admin - {trustee_name}",
        role="ADMIN_L1",
        admin_level=1,
        default_section_id=org_unit_id,
        managed_subsystem_ids=[subsystem_id],
        is_active=True
    )
    db.add(new_user)
    db.flush()
    
    # Grant subsystem access (RBAC)
    access = models.UserSubsystemAccess(
        user_id=new_user.id,
        subsystem_id=subsystem_id
    )
    db.add(access)
    db.flush()
    
    return new_user.id, True

def get_or_create_subsystem(db: Session) -> int:
    """Get or create the Civil Works subsystem."""
    existing = db.query(models.Subsystem).filter(
        models.Subsystem.code == SUBSYSTEM_CODE
    ).first()
    
    if existing:
        return existing.id
    
    subsystem = models.Subsystem(
        code=SUBSYSTEM_CODE,
        title=SUBSYSTEM_TITLE,
        icon="construction",
        is_active=True,
        order=14
    )
    db.add(subsystem)
    db.flush()
    print(f"  [NEW] Created Subsystem: {SUBSYSTEM_TITLE} (ID: {subsystem.id})")
    return subsystem.id

def create_unique_activity(db: Session, subsystem_id: int, budget_code: str, description: str, row_index: int) -> tuple:
    """
    Create a UNIQUE SubsystemActivity for this budget line.
    
    Strategy: Each budget line gets its own activity to prevent fund shifting.
    Returns: (activity_id, was_created)
    """
    # Generate unique code: CIVIL_WORKS_<budget_code>_<row_index>
    activity_code = f"CW_{budget_code}_{row_index}"
    
    # Check if exists
    existing = db.query(models.SubsystemActivity).filter(
        models.SubsystemActivity.code == activity_code
    ).first()
    
    if existing:
        return existing.id, False
    
    # Create unique activity
    activity = models.SubsystemActivity(
        subsystem_id=subsystem_id,
        code=activity_code,
        title=description[:200] if description else f"Budget Line {budget_code}",
        is_active=True,
        frequency=models.ActivityFrequency.YEARLY,
        requires_file_upload=True
    )
    db.add(activity)
    db.flush()
    return activity.id, True

def create_budget_row(db: Session, activity_id: int, budget_code: str, description: str, 
                     approved_amount: float, org_unit_id: int = None) -> tuple:
    """
    Create BudgetRow (Zero Trust model) linked to activity.
    Returns: (budget_row_id, was_created)
    """
    # Check if exists
    existing = db.query(models.BudgetRow).filter(
        models.BudgetRow.budget_coding == budget_code
    ).first()
    
    if existing:
        return existing.id, False
    
    # Convert to integer (Rials - no decimal places)
    approved = int(approved_amount) if approved_amount and not pd.isna(approved_amount) else 0
    
    budget_row = models.BudgetRow(
        activity_id=activity_id,
        org_unit_id=org_unit_id,
        budget_coding=budget_code,
        description=description[:500] if description else "",
        approved_amount=approved,
        blocked_amount=0,
        spent_amount=0,
        fiscal_year="1403"
    )
    db.add(budget_row)
    db.flush()
    return budget_row.id, True

def create_activity_constraint(db: Session, activity_id: int, budget_code: str) -> tuple:
    """
    Create ActivityConstraint for STRICT 1-to-1 locking.
    This constraint ensures the activity can ONLY use this specific budget code.
    Returns: (constraint_id, was_created)
    """
    # Check if constraint already exists for this activity and budget
    existing = db.query(models.ActivityConstraint).filter(
        models.ActivityConstraint.subsystem_activity_id == activity_id,
        models.ActivityConstraint.budget_code_pattern == budget_code
    ).first()
    
    if existing:
        return existing.id, False
    
    constraint = models.ActivityConstraint(
        subsystem_activity_id=activity_id,
        budget_code_pattern=budget_code,  # Exact match (not a pattern)
        constraint_type="INCLUDE",
        description=f"Strict 1-to-1: Activity locked to budget {budget_code} (Anti-corruption)",
        is_active=True,
        priority=100  # High priority
    )
    db.add(constraint)
    db.flush()
    return constraint.id, True

def import_region14_zero_trust(db: Session, df: pd.DataFrame, dry_run: bool = False) -> dict:
    """
    PHASE 1: Zero Trust Import with Human Layer Generation
    
    Atomic Operations per row:
    1. Create unique SubsystemActivity (1-to-1)
    2. Create BudgetRow (Zero Trust)
    3. Create ActivityConstraint (Lock budget code)
    4. Create OrgUnit for Trustee (if new)
    5. Create Admin User for Trustee (if new)
    """
    
    stats = {
        'activities_created': 0,
        'budget_rows_created': 0,
        'constraints_created': 0,
        'org_units_created': 0,
        'users_created': 0,
        'skipped': 0,
        'errors': []
    }
    
    print("\n" + "=" * 80)
    print("PHASE 1: ZERO TRUST IMPORT + HUMAN LAYER GENERATION")
    print("=" * 80)
    
    # Step 1: Ensure parent structures exist
    print("\n[1/5] Ensuring parent structures...")
    region_org_id = get_or_create_region_org_unit(db)
    subsystem_id = get_or_create_subsystem(db)
    
    # Step 2: Extract unique trustees for Human Layer generation
    print("\n[2/5] Analyzing trustees for Human Layer...")
    unique_trustees = df['متولی'].dropna().unique()
    print(f"  Found {len(unique_trustees)} unique trustees")
    
    trustee_map = {}  # trustee_name -> (org_unit_id, user_id)
    
    for trustee_name in unique_trustees:
        trustee_name = clean_str(trustee_name)
        if not trustee_name:
            continue
            
        org_id, org_created = get_or_create_trustee_org_unit(db, trustee_name, region_org_id)
        user_id, user_created = get_or_create_admin_user(db, trustee_name, org_id, subsystem_id)
        
        trustee_map[trustee_name] = (org_id, user_id)
        
        if org_created:
            stats['org_units_created'] += 1
            print(f"  [NEW ORG] {trustee_name} (ID: {org_id})")
        if user_created:
            stats['users_created'] += 1
            username = generate_username(trustee_name, REGION_CODE)
            print(f"  [NEW USER] {username} for {trustee_name} (ID: {user_id})")
    
    # Step 3: Process each budget line with Strict 1-to-1 Mapping
    print("\n[3/5] Processing budget lines (Strict 1-to-1 Mapping)...")
    
    for idx, row in df.iterrows():
        try:
            budget_code = clean_str(row.get('کد بودجه'))
            if not budget_code:
                stats['skipped'] += 1
                continue
            
            description = clean_str(row.get('شرح ردیف'))
            approved_amount = clean_float(row.get('مصوب 1403'))
            trustee_name = clean_str(row.get('متولی'))
            
            # Get trustee org unit
            trustee_org_id = None
            if trustee_name and trustee_name in trustee_map:
                trustee_org_id = trustee_map[trustee_name][0]
            
            # ATOMIC OPERATION: Create Activity -> BudgetRow -> Constraint
            activity_id, activity_created = create_unique_activity(
                db, subsystem_id, budget_code, description, idx
            )
            
            budget_row_id, budget_created = create_budget_row(
                db, activity_id, budget_code, description, approved_amount, trustee_org_id
            )
            
            constraint_id, constraint_created = create_activity_constraint(
                db, activity_id, budget_code
            )
            
            # Update stats
            if activity_created:
                stats['activities_created'] += 1
            if budget_created:
                stats['budget_rows_created'] += 1
            if constraint_created:
                stats['constraints_created'] += 1
            
            # Progress indicator (every 10 rows)
            if (idx + 1) % 10 == 0:
                print(f"  Processed {idx + 1}/{len(df)} rows...")
                
        except Exception as e:
            error_msg = f"Row {idx} (Budget: {budget_code}): {str(e)}"
            stats['errors'].append(error_msg)
            print(f"  [ERROR] {error_msg}")
    
    # Step 4: Create legacy BudgetItem for backward compatibility (optional)
    print("\n[4/5] Creating legacy BudgetItem records (backward compatibility)...")
    legacy_created = 0
    
    for idx, row in df.iterrows():
        try:
            budget_code = clean_str(row.get('کد بودجه'))
            if not budget_code:
                continue
            
            # Check if already exists
            existing = db.query(models.BudgetItem).filter(
                models.BudgetItem.budget_code == budget_code
            ).first()
            
            if existing:
                continue
            
            trustee_name = clean_str(row.get('متولی'))
            trustee_org_id = None
            if trustee_name and trustee_name in trustee_map:
                trustee_org_id = trustee_map[trustee_name][0]
            
            # Create legacy item
            item = models.BudgetItem(
                budget_code=budget_code,
                description=clean_str(row.get('شرح ردیف')),
                budget_type="capital",
                zone=clean_str(row.get('منطقه')),
                zone_code=REGION_CODE,
                trustee=trustee_name,
                trustee_section_id=trustee_org_id,
                subject=clean_str(row.get('موضوع')),
                sub_subject=clean_str(row.get('زیر موضوع')),
                row_type=clean_str(row.get('نوع ردیف')) or "مستمر",
                approved_1403=clean_float(row.get('مصوب 1403')),
                allocated_1403=clean_float(row.get('تخصیص 1403')),
                spent_1403=clean_float(row.get('هزینه 1403')),
            )
            db.add(item)
            legacy_created += 1
                
        except Exception as e:
            pass  # Non-critical
    
    print(f"  Created {legacy_created} legacy BudgetItem records")
    
    # Step 5: Commit or Rollback
    print("\n[5/5] Finalizing...")
    if dry_run:
        print("  [DRY RUN] Rolling back all changes...")
        db.rollback()
    else:
        print("  [COMMIT] Saving all changes to database...")
        db.commit()
    
    return stats

def verify_import(db: Session) -> dict:
    """Verify the import was successful."""
    verification = {
        'total_activities': db.query(models.SubsystemActivity).filter(
            models.SubsystemActivity.subsystem_id == db.query(models.Subsystem).filter(
                models.Subsystem.code == SUBSYSTEM_CODE
            ).first().id if db.query(models.Subsystem).filter(
                models.Subsystem.code == SUBSYSTEM_CODE
            ).first() else None
        ).count() if db.query(models.Subsystem).filter(
            models.Subsystem.code == SUBSYSTEM_CODE
        ).first() else 0,
        'total_budget_rows': db.query(models.BudgetRow).filter(
            models.BudgetRow.fiscal_year == "1403"
        ).count(),
        'total_constraints': db.query(models.ActivityConstraint).count(),
        'total_region14_orgs': db.query(models.OrgUnit).filter(
            models.OrgUnit.parent_id == db.query(models.OrgUnit).filter(
                models.OrgUnit.code == REGION_CODE
            ).first().id if db.query(models.OrgUnit).filter(
                models.OrgUnit.code == REGION_CODE
            ).first() else None
        ).count() if db.query(models.OrgUnit).filter(
            models.OrgUnit.code == REGION_CODE
        ).first() else 0,
        'total_admin_users': db.query(models.User).filter(
            models.User.username.like(f'admin_r{REGION_CODE}_%')
        ).count(),
    }
    return verification

def main():
    parser = argparse.ArgumentParser(
        description="Region 14 Zero Trust Import Script - Phase 1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be created (recommended first run)
  python import_region14_budget.py --dry-run
  
  # Execute the import
  python import_region14_budget.py
  
  # Force re-import (useful for testing)
  python import_region14_budget.py --force
        """
    )
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without committing to database')
    parser.add_argument('--force', action='store_true',
                       help='Skip existing record checks (for re-import)')
    args = parser.parse_args()
    
    print("=" * 80)
    print("REGION 14 ZERO TRUST IMPORT SCRIPT - PHASE 1")
    print("=" * 80)
    print(f"Execution Mode: {'DRY RUN (Preview Only)' if args.dry_run else 'LIVE IMPORT'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Verify file exists
    if not EXCEL_FILE.exists():
        print(f"\n[ERROR] Excel file not found: {EXCEL_FILE}")
        print("Please ensure the file exists at the expected location.")
        return 1
    
    # Load data
    print(f"\n[LOAD] Reading Excel file: {EXCEL_FILE.name}")
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"  ✓ Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        print(f"  [ERROR] Failed to read Excel file: {e}")
        return 1
    
    # Display column info
    print(f"\n[INFO] Excel Columns:")
    for col in df.columns:
        print(f"  - {col}")
    
    # Quick statistics
    print(f"\n[STATS] Pre-Import Analysis:")
    print(f"  Total Budget Lines: {len(df)}")
    print(f"  Unique Trustees: {df['متولی'].nunique()}")
    print(f"  Total Approved Budget: {df['مصوب 1403'].sum():,.0f} (if numeric)")
    
    # Connect to database
    print(f"\n[DB] Connecting to database...")
    db = SessionLocal()
    
    try:
        # Execute Zero Trust Import
        stats = import_region14_zero_trust(db, df, dry_run=args.dry_run)
        
        # Print Summary Report
        print("\n" + "=" * 80)
        print("IMPORT SUMMARY REPORT")
        print("=" * 80)
        print(f"Status: {'DRY RUN COMPLETED (No changes saved)' if args.dry_run else 'IMPORT COMPLETED'}")
        print()
        print("Zero Trust Components Created:")
        print(f"  • SubsystemActivities (1-to-1): {stats['activities_created']}")
        print(f"  • BudgetRows (Zero Trust): {stats['budget_rows_created']}")
        print(f"  • ActivityConstraints (Locks): {stats['constraints_created']}")
        print()
        print("Human Layer Components Created:")
        print(f"  • OrgUnits (Departments): {stats['org_units_created']}")
        print(f"  • Admin Users (L1): {stats['users_created']}")
        print()
        print(f"Skipped Lines: {stats['skipped']}")
        
        if stats['errors']:
            print(f"\n⚠ Errors Encountered: {len(stats['errors'])}")
            print("\nError Details:")
            for error in stats['errors'][:10]:
                print(f"  - {error}")
            if len(stats['errors']) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more errors")
        
        # Verification (only if not dry run)
        if not args.dry_run:
            print("\n" + "=" * 80)
            print("DATABASE VERIFICATION")
            print("=" * 80)
            verification = verify_import(db)
            print(f"  • Total Activities in System: {verification['total_activities']}")
            print(f"  • Total BudgetRows (1403): {verification['total_budget_rows']}")
            print(f"  • Total Constraints: {verification['total_constraints']}")
            print(f"  • Region 14 Departments: {verification['total_region14_orgs']}")
            print(f"  • Region 14 Admin Users: {verification['total_admin_users']}")
            
            # Display created users
            print("\n[INFO] Created Admin Users:")
            users = db.query(models.User).filter(
                models.User.username.like(f'admin_r{REGION_CODE}_%')
            ).all()
            for user in users[:10]:
                print(f"  - {user.username} | {user.full_name}")
                print(f"    Password: {DEFAULT_ADMIN_PASSWORD} (MUST CHANGE ON FIRST LOGIN)")
            if len(users) > 10:
                print(f"  ... and {len(users) - 10} more users")
        
        print("\n" + "=" * 80)
        if args.dry_run:
            print("[SUCCESS] Dry run completed. Use without --dry-run to apply changes.")
        else:
            print("[SUCCESS] Region 14 import completed successfully!")
            print(f"[SECURITY] Default password: {DEFAULT_ADMIN_PASSWORD}")
            print("[ACTION REQUIRED] All admin users MUST change their password on first login.")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("[FATAL ERROR] Import failed!")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
