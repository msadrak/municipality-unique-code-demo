"""
🚀 Master System Seeder
======================

This script orchestrates the entire seeding process for the Municipality system.

Layer 1 (Reference Data):
- Organizational units from Excel
- Budget items from Excel

Layer 2 (Configuration Data):
- Subsystems, Activities, and Constraints from config_master.json
- Uses UPSERT logic for idempotent execution

Usage:
    python seed_full_system.py              # Full seed
    python seed_full_system.py --dry-run    # Preview only
    python seed_full_system.py --layer2     # Only Layer 2 (config data)
"""

import sys
import os
import argparse
from datetime import datetime

# Ensure we can import from 'app' when running as standalone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models import (
    Base, 
    Subsystem, 
    SubsystemActivity, 
    ActivityConstraint,
    ActivityFrequency
)
from app.utils.config_loader import load_and_validate_config, ConfigLoadError


# ============================================
# Layer 1: Reference Data Seeders
# ============================================

def seed_layer1_org_units():
    """Import organizational units from Excel."""
    print("\n📂 Layer 1: Seeding Organizational Units...")
    try:
        from seed_org import seed_org_units
        seed_org_units()
        print("   ✅ Organizational units seeded successfully")
        return True
    except ImportError as e:
        print(f"   ⚠️  Could not import seed_org: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error seeding org units: {e}")
        return False


def seed_layer1_budget(dry_run: bool = False):
    """Import budget items from Excel."""
    print("\n💰 Layer 1: Seeding Budget Items...")
    try:
        from app.adapters import BudgetAdapter
        
        # Try common budget file paths
        budget_files = [
            "budget.xlsx",
            "اعتبارات هزینه ای.xlsx",
            "تملک دارایی سرمایه ای.xlsx"
        ]
        
        for budget_file in budget_files:
            if os.path.exists(budget_file):
                print(f"   📄 Found: {budget_file}")
                adapter = BudgetAdapter(budget_file)
                results = adapter.import_to_db(dry_run=dry_run)
                print(f"   ✅ Budget import: {results['success']} success, {results['updated']} updated")
                return True
        
        print("   ⚠️  No budget Excel file found, skipping...")
        return False
        
    except ImportError as e:
        print(f"   ⚠️  Could not import BudgetAdapter: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error seeding budget: {e}")
        return False


# ============================================
# Layer 2: Configuration Data Seeder
# ============================================

def seed_layer2_config(dry_run: bool = False) -> dict:
    """
    Seed Subsystems, Activities, and Constraints from config_master.json.
    
    Uses UPSERT logic:
    - If subsystem/activity exists (by code), UPDATE it
    - If not exists, INSERT it
    - For constraints: DELETE all old and INSERT new (full sync)
    
    Returns:
        dict: Statistics about what was created/updated
    """
    print("\n⚙️  Layer 2: Seeding Configuration from JSON...")
    
    stats = {
        "subsystems_created": 0,
        "subsystems_updated": 0,
        "activities_created": 0,
        "activities_updated": 0,
        "constraints_cleared": 0,
        "constraints_created": 0,
        "errors": []
    }
    
    # Load and validate config
    try:
        config = load_and_validate_config("app/config/config_master.json")
    except ConfigLoadError as e:
        print(f"   ❌ {e}")
        stats["errors"].append(str(e))
        return stats
    
    if dry_run:
        print("   🔍 DRY RUN - No changes will be made")
        for sub in config.subsystems:
            print(f"      Would process: {sub.code} ({sub.title}) - {len(sub.activities)} activities")
        return stats
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Ensure tables exist
        Base.metadata.create_all(bind=engine)
        
        for sub_config in config.subsystems:
            # ----- UPSERT Subsystem -----
            existing_subsystem = db.query(Subsystem).filter(
                Subsystem.code == sub_config.code
            ).first()
            
            if existing_subsystem:
                # UPDATE
                existing_subsystem.title = sub_config.title
                existing_subsystem.icon = sub_config.icon
                existing_subsystem.attachment_type = sub_config.attachment_type
                existing_subsystem.order = sub_config.order
                existing_subsystem.is_active = sub_config.is_active
                db.flush()
                subsystem = existing_subsystem
                stats["subsystems_updated"] += 1
                print(f"   🔄 Updated subsystem: {sub_config.code}")
            else:
                # INSERT
                subsystem = Subsystem(
                    code=sub_config.code,
                    title=sub_config.title,
                    icon=sub_config.icon,
                    attachment_type=sub_config.attachment_type,
                    order=sub_config.order,
                    is_active=sub_config.is_active
                )
                db.add(subsystem)
                db.flush()
                stats["subsystems_created"] += 1
                print(f"   ✨ Created subsystem: {sub_config.code}")
            
            # ----- Process Activities -----
            for act_config in sub_config.activities:
                existing_activity = db.query(SubsystemActivity).filter(
                    SubsystemActivity.subsystem_id == subsystem.id,
                    SubsystemActivity.code == act_config.code
                ).first()
                
                # Map frequency string to enum
                frequency_enum = ActivityFrequency[act_config.frequency]
                
                if existing_activity:
                    # UPDATE activity
                    existing_activity.title = act_config.title
                    existing_activity.form_type = act_config.form_type
                    existing_activity.frequency = frequency_enum
                    existing_activity.requires_file_upload = act_config.requires_file_upload
                    existing_activity.external_service_url = act_config.external_service_url
                    existing_activity.order = act_config.order
                    existing_activity.is_active = act_config.is_active
                    db.flush()
                    activity = existing_activity
                    stats["activities_updated"] += 1
                    print(f"      🔄 Updated activity: {act_config.code}")
                else:
                    # INSERT activity
                    activity = SubsystemActivity(
                        subsystem_id=subsystem.id,
                        code=act_config.code,
                        title=act_config.title,
                        form_type=act_config.form_type,
                        frequency=frequency_enum,
                        requires_file_upload=act_config.requires_file_upload,
                        external_service_url=act_config.external_service_url,
                        order=act_config.order,
                        is_active=act_config.is_active
                    )
                    db.add(activity)
                    db.flush()
                    stats["activities_created"] += 1
                    print(f"      ✨ Created activity: {act_config.code}")
                
                # ----- Sync Constraints -----
                # Delete existing constraints for this activity
                deleted_count = db.query(ActivityConstraint).filter(
                    ActivityConstraint.subsystem_activity_id == activity.id
                ).delete()
                stats["constraints_cleared"] += deleted_count
                
                # Insert new constraints from config
                for constraint_config in act_config.constraints:
                    constraint = ActivityConstraint(
                        subsystem_activity_id=activity.id,
                        budget_code_pattern=constraint_config.budget_code_pattern,
                        allowed_budget_types=constraint_config.allowed_budget_types,
                        cost_center_pattern=constraint_config.cost_center_pattern,
                        allowed_cost_centers=constraint_config.allowed_cost_centers,
                        constraint_type=constraint_config.constraint_type,
                        priority=constraint_config.priority,
                        description=constraint_config.description,
                        is_active=True
                    )
                    db.add(constraint)
                    stats["constraints_created"] += 1
                
                if act_config.constraints:
                    print(f"         📋 Synced {len(act_config.constraints)} constraint(s)")
        
        # Commit all changes
        db.commit()
        print("\n   ✅ Layer 2 seeding completed successfully")
        
    except Exception as e:
        db.rollback()
        error_msg = f"Error during Layer 2 seeding: {e}"
        print(f"   ❌ {error_msg}")
        stats["errors"].append(error_msg)
        raise
    finally:
        db.close()
    
    return stats


# ============================================
# Main Entry Point
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Master System Seeder - Seeds all reference and configuration data"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview changes without modifying the database"
    )
    parser.add_argument(
        "--layer1",
        action="store_true",
        help="Only run Layer 1 (reference data: org units, budget)"
    )
    parser.add_argument(
        "--layer2",
        action="store_true",
        help="Only run Layer 2 (configuration data from JSON)"
    )
    parser.add_argument(
        "--skip-org",
        action="store_true",
        help="Skip organizational units seeding"
    )
    parser.add_argument(
        "--skip-budget",
        action="store_true",
        help="Skip budget items seeding"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 MASTER SYSTEM SEEDER")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("   Mode: DRY RUN (no changes will be made)")
    print("=" * 60)
    
    # Determine which layers to run
    run_layer1 = not args.layer2  # Run Layer1 unless --layer2 only
    run_layer2 = not args.layer1  # Run Layer2 unless --layer1 only
    
    # If both flags are set, run both (full seed)
    if args.layer1 and args.layer2:
        run_layer1 = True
        run_layer2 = True
    
    # ---- Layer 1 ----
    if run_layer1:
        print("\n" + "=" * 60)
        print("📦 LAYER 1: REFERENCE DATA")
        print("=" * 60)
        
        if not args.skip_org:
            seed_layer1_org_units()
        else:
            print("\n   ⏭️  Skipping org units (--skip-org)")
        
        if not args.skip_budget:
            seed_layer1_budget(dry_run=args.dry_run)
        else:
            print("\n   ⏭️  Skipping budget (--skip-budget)")
    
    # ---- Layer 2 ----
    if run_layer2:
        print("\n" + "=" * 60)
        print("📦 LAYER 2: CONFIGURATION DATA")
        print("=" * 60)
        
        stats = seed_layer2_config(dry_run=args.dry_run)
        
        # Print summary
        print("\n" + "-" * 40)
        print("📊 Layer 2 Summary:")
        print(f"   Subsystems: {stats['subsystems_created']} created, {stats['subsystems_updated']} updated")
        print(f"   Activities: {stats['activities_created']} created, {stats['activities_updated']} updated")
        print(f"   Constraints: {stats['constraints_cleared']} cleared, {stats['constraints_created']} created")
        if stats["errors"]:
            print(f"   Errors: {len(stats['errors'])}")
    
    print("\n" + "=" * 60)
    print(f"✅ SEEDING COMPLETED at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
