"""
Diagnostic Script: Debug Budget Display Issue
==============================================

This script queries the database to answer:
1. How many BudgetRow records exist for a specific activity?
2. What are the org_unit_id values for those records?
3. What is the actual data state vs. expected state?

NO DATA MODIFICATIONS - READ-ONLY QUERIES
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import (
    BudgetRow, 
    SubsystemActivity, 
    Subsystem,
    OrgUnit,
    User
)


def print_separator(title: str = ""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def debug_activities(db: Session):
    """List all activities and their potential keywords."""
    print_separator("ALL SUBSYSTEM ACTIVITIES")
    
    activities = db.query(SubsystemActivity).join(Subsystem).all()
    
    if not activities:
        print("❌ NO ACTIVITIES FOUND IN DATABASE!")
        return
    
    print(f"Found {len(activities)} activities:\n")
    for act in activities:
        print(f"  ID={act.id:3d} | Subsystem: {act.subsystem.title if act.subsystem else 'N/A':20s} | Code: {act.code:20s} | Title: {act.title}")


def find_land_acquisition_activity(db: Session) -> SubsystemActivity | None:
    """Find the Land Acquisition activity by searching for keywords."""
    
    # Keywords to search for
    keywords = ["تملک", "Land", "Acquisition", "LAND_ACQUISITION"]
    
    for keyword in keywords:
        activity = db.query(SubsystemActivity).filter(
            SubsystemActivity.title.ilike(f"%{keyword}%") |
            SubsystemActivity.code.ilike(f"%{keyword}%")
        ).first()
        
        if activity:
            return activity
    
    return None


def debug_budget_rows_for_activity(db: Session, activity_id: int):
    """Query budget rows for a specific activity."""
    print_separator(f"BUDGET ROWS FOR ACTIVITY ID={activity_id}")
    
    # Get activity details first
    activity = db.query(SubsystemActivity).filter(SubsystemActivity.id == activity_id).first()
    if not activity:
        print(f"❌ Activity ID={activity_id} not found!")
        return
    
    print(f"Activity: {activity.title} (Code: {activity.code})")
    if activity.subsystem:
        print(f"Subsystem: {activity.subsystem.title} (ID: {activity.subsystem_id})")
    
    # Query budget rows
    budget_rows = db.query(BudgetRow).filter(BudgetRow.activity_id == activity_id).all()
    
    print(f"\n📊 Total BudgetRow records: {len(budget_rows)}")
    
    if len(budget_rows) == 0:
        print("\n❌ DATABASE IS EMPTY FOR THIS ACTIVITY!")
        print("   This means:")
        print("   - The seeder failed to match this activity")
        print("   - OR the activity was never seeded with budget data")
        print("\n   👉 NEXT STEP: Run inject_test_budget.py to manually add test data")
        return
    
    print("\n📋 Budget Row Details:")
    print("-" * 80)
    print(f"{'ID':>5} | {'org_unit_id':>12} | {'Approved':>15} | {'Spent':>12} | {'Blocked':>12} | Description")
    print("-" * 80)
    
    for row in budget_rows:
        org_unit_display = str(row.org_unit_id) if row.org_unit_id else "NULL (Global)"
        approved_display = f"{row.approved_amount:,}" if row.approved_amount else "0"
        spent_display = f"{row.spent_amount:,}" if row.spent_amount else "0"
        blocked_display = f"{row.blocked_amount:,}" if row.blocked_amount else "0"
        
        print(f"{row.id:>5} | {org_unit_display:>12} | {approved_display:>15} | {spent_display:>12} | {blocked_display:>12} | {row.description[:30] if row.description else 'N/A'}...")
    
    # Analyze org_unit_id distribution
    print("\n📊 org_unit_id Analysis:")
    null_count = sum(1 for r in budget_rows if r.org_unit_id is None)
    not_null_count = len(budget_rows) - null_count
    
    print(f"   NULL (Global HQ): {null_count}")
    print(f"   Assigned to Zone: {not_null_count}")
    
    # Get unique org_unit_ids
    org_unit_ids = set(r.org_unit_id for r in budget_rows if r.org_unit_id is not None)
    if org_unit_ids:
        print(f"\n   Unique org_unit_ids: {sorted(org_unit_ids)}")
        
        # Look up org_unit names
        for org_id in sorted(org_unit_ids):
            org_unit = db.query(OrgUnit).filter(OrgUnit.id == org_id).first()
            if org_unit:
                print(f"      ID={org_id}: {org_unit.title} (Type: {org_unit.org_type})")


def debug_all_budget_rows(db: Session):
    """Show overall budget row statistics."""
    print_separator("OVERALL BUDGET ROW STATISTICS")
    
    total = db.query(BudgetRow).count()
    print(f"Total BudgetRow records in database: {total}")
    
    if total == 0:
        print("\n❌ NO BUDGET ROWS IN DATABASE AT ALL!")
        return
    
    # Group by activity
    from sqlalchemy import func
    activity_counts = db.query(
        SubsystemActivity.id,
        SubsystemActivity.title,
        func.count(BudgetRow.id).label('budget_count')
    ).join(
        BudgetRow, BudgetRow.activity_id == SubsystemActivity.id
    ).group_by(
        SubsystemActivity.id, SubsystemActivity.title
    ).all()
    
    print(f"\nActivities with budget rows ({len(activity_counts)} activities):")
    for act_id, act_title, count in activity_counts:
        print(f"   ID={act_id:3d}: {count:5d} rows | {act_title}")


def debug_org_units(db: Session):
    """List zones/regions for reference."""
    print_separator("ORGANIZATIONAL UNITS (ZONES)")
    
    zones = db.query(OrgUnit).filter(OrgUnit.org_type == "zone").all()
    
    if not zones:
        # Try without filter
        zones = db.query(OrgUnit).limit(10).all()
        print("(No 'zone' type found, showing first 10 org_units)")
    
    for zone in zones:
        print(f"   ID={zone.id:3d} | Code: {zone.code:10s} | Type: {zone.org_type:10s} | {zone.title}")


def debug_users(db: Session):
    """Show user zone assignments."""
    print_separator("USER ZONE ASSIGNMENTS")
    
    users = db.query(User).all()
    
    for user in users:
        zone_info = "N/A"
        if user.default_zone_id:
            zone = db.query(OrgUnit).filter(OrgUnit.id == user.default_zone_id).first()
            zone_info = f"ID={user.default_zone_id} ({zone.title if zone else 'Not Found'})"
        
        print(f"   {user.username:20s} | Zone: {zone_info}")


def debug_subsystems(db: Session):
    """List all subsystems with their IDs."""
    print_separator("ALL SUBSYSTEMS")
    
    subsystems = db.query(Subsystem).order_by(Subsystem.id).all()
    
    if not subsystems:
        print("❌ NO SUBSYSTEMS FOUND IN DATABASE!")
        return
    
    print(f"Found {len(subsystems)} subsystems:\n")
    print(f"{'ID':>4} | {'Code':20s} | Title")
    print("-" * 60)
    for sub in subsystems:
        print(f"{sub.id:>4} | {sub.code:20s} | {sub.title}")


def main():
    print("\n" + "🔍" * 30)
    print("  BUDGET DATABASE DIAGNOSTIC TOOL")
    print("🔍" * 30)
    
    db = SessionLocal()
    try:
        # Step 0: Show all subsystems
        debug_subsystems(db)
        
        # Step 1: Show all activities
        debug_activities(db)
        
        # Step 2: Find Land Acquisition activity
        print_separator("SEARCHING FOR 'LAND ACQUISITION' ACTIVITY")
        land_activity = find_land_acquisition_activity(db)
        
        if land_activity:
            print(f"✅ Found: ID={land_activity.id} | {land_activity.title} | Code: {land_activity.code}")
            
            # Step 3: Debug budget rows for this activity
            debug_budget_rows_for_activity(db, land_activity.id)
        else:
            print("❌ 'Land Acquisition' activity NOT FOUND!")
            print("   Please check the activity list above and specify a different keyword.")
        
        # Step 4: Overall statistics
        debug_all_budget_rows(db)
        
        # Step 5: Org units reference
        debug_org_units(db)
        
        # Step 6: User assignments
        debug_users(db)
        
        print_separator("DIAGNOSTIC COMPLETE")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
