"""
Seed Region 14 Organizational Structure
========================================
This script creates the base organizational structure for Region 14
before importing budget data. Run this BEFORE import_region14_budget.py
if you need to manually set up the hierarchy.

Usage:
    python seed_region14_structure.py           # Create structure
    python seed_region14_structure.py --verify  # Verify only (no changes)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from app.database import SessionLocal
from app import models

REGION_CODE = "14"
REGION_NAME = "منطقه چهارده"
SUBSYSTEM_CODE = "CIVIL_WORKS"
SUBSYSTEM_TITLE = "عمران و طرح‌ها"


def create_region_hierarchy(db, dry_run=False):
    """Create Region 14 organizational hierarchy."""
    
    print("=" * 80)
    print("REGION 14 ORGANIZATIONAL STRUCTURE SEEDER")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (Preview)' if dry_run else 'LIVE (Creating)'}\n")
    
    created_count = 0
    
    # 1. Create Region 14 Zone (if not exists)
    print("[1/2] Creating Region 14 Zone...")
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE,
        models.OrgUnit.org_type == "ZONE"
    ).first()
    
    if region:
        print(f"  ✓ Already exists: {region.title} (ID: {region.id})")
    else:
        if not dry_run:
            region = models.OrgUnit(
                title=REGION_NAME,
                code=REGION_CODE,
                org_type="ZONE"
            )
            db.add(region)
            db.flush()
            print(f"  ✓ CREATED: {region.title} (ID: {region.id})")
        else:
            print(f"  → Would create: {REGION_NAME}")
        created_count += 1
    
    # 2. Create Civil Works Subsystem (if not exists)
    print("\n[2/2] Creating Civil Works Subsystem...")
    subsystem = db.query(models.Subsystem).filter(
        models.Subsystem.code == SUBSYSTEM_CODE
    ).first()
    
    if subsystem:
        print(f"  ✓ Already exists: {subsystem.title} (ID: {subsystem.id})")
    else:
        if not dry_run:
            subsystem = models.Subsystem(
                code=SUBSYSTEM_CODE,
                title=SUBSYSTEM_TITLE,
                icon="construction",
                is_active=True,
                order=14,
                attachment_type="upload"
            )
            db.add(subsystem)
            db.flush()
            print(f"  ✓ CREATED: {subsystem.title} (ID: {subsystem.id})")
        else:
            print(f"  → Would create: {SUBSYSTEM_TITLE}")
        created_count += 1
    
    # Commit changes
    if not dry_run and created_count > 0:
        db.commit()
        print(f"\n✓ Successfully created {created_count} record(s)")
    elif dry_run:
        print(f"\n→ Would create {created_count} record(s)")
        db.rollback()
    else:
        print("\n✓ All structures already exist")
    
    return created_count


def verify_structure(db):
    """Verify the Region 14 structure."""
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    all_ok = True
    
    # Check Region
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE,
        models.OrgUnit.org_type == "ZONE"
    ).first()
    
    if region:
        print(f"✓ Region 14 exists: {region.title} (ID: {region.id})")
        
        # Check departments under region
        dept_count = db.query(models.OrgUnit).filter(
            models.OrgUnit.parent_id == region.id
        ).count()
        print(f"  - Departments: {dept_count}")
    else:
        print("✗ Region 14 NOT FOUND")
        all_ok = False
    
    # Check Subsystem
    subsystem = db.query(models.Subsystem).filter(
        models.Subsystem.code == SUBSYSTEM_CODE
    ).first()
    
    if subsystem:
        print(f"✓ Civil Works subsystem exists: {subsystem.title} (ID: {subsystem.id})")
        
        # Check activities
        activity_count = db.query(models.SubsystemActivity).filter(
            models.SubsystemActivity.subsystem_id == subsystem.id
        ).count()
        print(f"  - Activities: {activity_count}")
    else:
        print("✗ Civil Works subsystem NOT FOUND")
        all_ok = False
    
    print("\n" + "=" * 80)
    if all_ok:
        print("✓ VERIFICATION PASSED - Structure is ready for import")
    else:
        print("✗ VERIFICATION FAILED - Run seeder to create missing structures")
    print("=" * 80)
    
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Seed Region 14 Organizational Structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be created
  python seed_region14_structure.py --dry-run
  
  # Create the structure
  python seed_region14_structure.py
  
  # Verify structure exists
  python seed_region14_structure.py --verify
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without committing')
    parser.add_argument('--verify', action='store_true',
                       help='Only verify structure (no changes)')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        if args.verify:
            # Verification mode
            verify_structure(db)
        else:
            # Creation mode
            created = create_region_hierarchy(db, dry_run=args.dry_run)
            
            # Always verify after
            if created > 0 or not args.dry_run:
                verify_structure(db)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
