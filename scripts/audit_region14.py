"""
Region 14 Audit and Verification Script
========================================
This script verifies the integrity of Region 14 Zero Trust deployment.

Usage:
    python audit_region14.py                    # Full audit
    python audit_region14.py --trustees         # Show trustees only
    python audit_region14.py --users            # Show users only
    python audit_region14.py --budget-summary   # Budget summary
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from sqlalchemy import func
from app.database import SessionLocal
from app import models

REGION_CODE = "14"
SUBSYSTEM_CODE = "CIVIL_WORKS"


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def audit_region_structure(db):
    """Audit Region 14 organizational structure."""
    print_header("REGION 14 ORGANIZATIONAL STRUCTURE")
    
    # Get region
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE
    ).first()
    
    if not region:
        print("⚠️  ERROR: Region 14 OrgUnit not found!")
        return False
    
    print(f"✓ Region: {region.title} (ID: {region.id}, Code: {region.code})")
    
    # Get departments under region
    departments = db.query(models.OrgUnit).filter(
        models.OrgUnit.parent_id == region.id
    ).all()
    
    print(f"\n✓ Departments: {len(departments)}")
    for dept in departments:
        print(f"  • {dept.title}")
        print(f"    - ID: {dept.id}")
        print(f"    - Code: {dept.code}")
        print(f"    - Type: {dept.org_type}")
    
    return True


def audit_subsystem(db):
    """Audit Civil Works subsystem."""
    print_header("CIVIL WORKS SUBSYSTEM")
    
    subsystem = db.query(models.Subsystem).filter(
        models.Subsystem.code == SUBSYSTEM_CODE
    ).first()
    
    if not subsystem:
        print("⚠️  ERROR: Civil Works subsystem not found!")
        return False
    
    print(f"✓ Subsystem: {subsystem.title}")
    print(f"  - ID: {subsystem.id}")
    print(f"  - Code: {subsystem.code}")
    print(f"  - Active: {subsystem.is_active}")
    
    # Count activities
    activity_count = db.query(models.SubsystemActivity).filter(
        models.SubsystemActivity.subsystem_id == subsystem.id
    ).count()
    
    print(f"  - Total Activities: {activity_count}")
    
    return True


def audit_users(db):
    """Audit Region 14 admin users."""
    print_header("ADMIN USERS")
    
    users = db.query(models.User).filter(
        models.User.username.like(f'admin_r{REGION_CODE}_%')
    ).all()
    
    print(f"✓ Total Admin Users: {len(users)}")
    
    if not users:
        print("⚠️  WARNING: No admin users found for Region 14")
        return False
    
    print("\nUser Details:")
    for user in users:
        print(f"\n  • Username: {user.username}")
        print(f"    - Full Name: {user.full_name}")
        print(f"    - Role: {user.role} (Level {user.admin_level})")
        print(f"    - Active: {user.is_active}")
        print(f"    - Default Section: {user.default_section.title if user.default_section else 'N/A'}")
        
        # Check subsystem access
        access = db.query(models.UserSubsystemAccess).filter(
            models.UserSubsystemAccess.user_id == user.id
        ).all()
        print(f"    - Subsystem Access: {len(access)} subsystem(s)")
        for acc in access:
            print(f"      → {acc.subsystem.title}")
    
    return True


def audit_budget_rows(db):
    """Audit BudgetRow records."""
    print_header("BUDGET ROWS (ZERO TRUST MODEL)")
    
    # Get Region 14 org unit
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE
    ).first()
    
    if not region:
        print("⚠️  Cannot audit: Region not found")
        return False
    
    # Get departments
    dept_ids = [d.id for d in db.query(models.OrgUnit).filter(
        models.OrgUnit.parent_id == region.id
    ).all()]
    
    # Count budget rows linked to Region 14 departments
    budget_rows = db.query(models.BudgetRow).filter(
        models.BudgetRow.org_unit_id.in_(dept_ids)
    ).all() if dept_ids else []
    
    print(f"✓ Total BudgetRows: {len(budget_rows)}")
    
    if not budget_rows:
        print("⚠️  WARNING: No budget rows found for Region 14")
        return False
    
    # Calculate totals
    total_approved = sum(br.approved_amount for br in budget_rows)
    total_spent = sum(br.spent_amount for br in budget_rows)
    total_blocked = sum(br.blocked_amount for br in budget_rows)
    total_remaining = sum(br.remaining_balance for br in budget_rows)
    
    print(f"\nBudget Summary (in Rials):")
    print(f"  • Total Approved:  {total_approved:>20,}")
    print(f"  • Total Spent:     {total_spent:>20,}")
    print(f"  • Total Blocked:   {total_blocked:>20,}")
    print(f"  • Total Remaining: {total_remaining:>20,}")
    print(f"  • Utilization:     {(total_spent / total_approved * 100) if total_approved > 0 else 0:>19.2f}%")
    
    # Sample records
    print(f"\nSample Budget Rows (first 5):")
    for br in budget_rows[:5]:
        print(f"\n  • Budget Code: {br.budget_coding}")
        print(f"    - Description: {br.description[:60]}...")
        print(f"    - Approved: {br.approved_amount:,}")
        print(f"    - Remaining: {br.remaining_balance:,}")
        print(f"    - Activity: {br.activity.title[:50]}..." if br.activity else "    - Activity: N/A")
    
    return True


def audit_constraints(db):
    """Audit ActivityConstraint records."""
    print_header("ACTIVITY CONSTRAINTS (1-TO-1 LOCKS)")
    
    # Get subsystem
    subsystem = db.query(models.Subsystem).filter(
        models.Subsystem.code == SUBSYSTEM_CODE
    ).first()
    
    if not subsystem:
        print("⚠️  Cannot audit: Subsystem not found")
        return False
    
    # Get constraints for this subsystem's activities
    constraints = db.query(models.ActivityConstraint).join(
        models.SubsystemActivity
    ).filter(
        models.SubsystemActivity.subsystem_id == subsystem.id
    ).all()
    
    print(f"✓ Total Constraints: {len(constraints)}")
    
    if not constraints:
        print("⚠️  WARNING: No constraints found for Civil Works activities")
        return False
    
    # Analyze constraint types
    include_count = sum(1 for c in constraints if c.constraint_type == "INCLUDE")
    exclude_count = sum(1 for c in constraints if c.constraint_type == "EXCLUDE")
    active_count = sum(1 for c in constraints if c.is_active)
    
    print(f"\nConstraint Breakdown:")
    print(f"  • INCLUDE (whitelist): {include_count}")
    print(f"  • EXCLUDE (blacklist): {exclude_count}")
    print(f"  • Active: {active_count}")
    print(f"  • Inactive: {len(constraints) - active_count}")
    
    # Sample constraints
    print(f"\nSample Constraints (first 5):")
    for constraint in constraints[:5]:
        print(f"\n  • Constraint ID: {constraint.id}")
        print(f"    - Activity: {constraint.activity.title[:50]}..." if constraint.activity else "    - Activity: N/A")
        print(f"    - Budget Pattern: {constraint.budget_code_pattern}")
        print(f"    - Type: {constraint.constraint_type}")
        print(f"    - Priority: {constraint.priority}")
        print(f"    - Description: {constraint.description[:60]}..." if constraint.description else "")
    
    return True


def audit_integrity(db):
    """Perform integrity checks."""
    print_header("INTEGRITY CHECKS")
    
    checks_passed = 0
    checks_total = 0
    
    # Check 1: Every BudgetRow has an Activity
    checks_total += 1
    orphaned_rows = db.query(models.BudgetRow).filter(
        models.BudgetRow.activity_id == None
    ).count()
    if orphaned_rows == 0:
        print("✓ Check 1: All BudgetRows have linked Activities")
        checks_passed += 1
    else:
        print(f"✗ Check 1 FAILED: {orphaned_rows} BudgetRows without Activities")
    
    # Check 2: Every Activity has at least one Constraint
    checks_total += 1
    subsystem = db.query(models.Subsystem).filter(
        models.Subsystem.code == SUBSYSTEM_CODE
    ).first()
    
    if subsystem:
        activities_without_constraints = db.query(models.SubsystemActivity).filter(
            models.SubsystemActivity.subsystem_id == subsystem.id,
            ~models.SubsystemActivity.constraints.any()
        ).count()
        
        if activities_without_constraints == 0:
            print("✓ Check 2: All Activities have Constraints")
            checks_passed += 1
        else:
            print(f"✗ Check 2 FAILED: {activities_without_constraints} Activities without Constraints")
    
    # Check 3: Every Admin User has Subsystem Access
    checks_total += 1
    users_without_access = db.query(models.User).filter(
        models.User.username.like(f'admin_r{REGION_CODE}_%'),
        ~models.User.subsystem_access_list.any()
    ).count()
    
    if users_without_access == 0:
        print("✓ Check 3: All Admin Users have Subsystem Access")
        checks_passed += 1
    else:
        print(f"✗ Check 3 FAILED: {users_without_access} Users without Subsystem Access")
    
    # Check 4: Budget integrity (spent + blocked <= approved)
    checks_total += 1
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE
    ).first()
    
    if region:
        dept_ids = [d.id for d in db.query(models.OrgUnit).filter(
            models.OrgUnit.parent_id == region.id
        ).all()]
        
        violated_budgets = db.query(models.BudgetRow).filter(
            models.BudgetRow.org_unit_id.in_(dept_ids),
            models.BudgetRow.spent_amount + models.BudgetRow.blocked_amount > models.BudgetRow.approved_amount
        ).count() if dept_ids else 0
        
        if violated_budgets == 0:
            print("✓ Check 4: All BudgetRows respect spending limits")
            checks_passed += 1
        else:
            print(f"✗ Check 4 FAILED: {violated_budgets} BudgetRows violate limits")
    
    # Check 5: Unique budget codes
    checks_total += 1
    duplicate_codes = db.query(
        models.BudgetRow.budget_coding,
        func.count(models.BudgetRow.id)
    ).group_by(
        models.BudgetRow.budget_coding
    ).having(
        func.count(models.BudgetRow.id) > 1
    ).count()
    
    if duplicate_codes == 0:
        print("✓ Check 5: All BudgetRow codes are unique")
        checks_passed += 1
    else:
        print(f"✗ Check 5 FAILED: {duplicate_codes} duplicate budget codes found")
    
    print(f"\n{'=' * 80}")
    print(f"INTEGRITY SCORE: {checks_passed}/{checks_total} checks passed")
    if checks_passed == checks_total:
        print("✓ ALL CHECKS PASSED - System integrity verified")
    else:
        print(f"⚠️  {checks_total - checks_passed} check(s) failed - Review required")
    
    return checks_passed == checks_total


def show_trustees(db):
    """Show all trustees and their admins."""
    print_header("TRUSTEES AND THEIR ADMIN USERS")
    
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE
    ).first()
    
    if not region:
        print("⚠️  Region 14 not found")
        return
    
    departments = db.query(models.OrgUnit).filter(
        models.OrgUnit.parent_id == region.id
    ).order_by(models.OrgUnit.title).all()
    
    for dept in departments:
        print(f"\n📋 {dept.title}")
        print(f"   ID: {dept.id} | Code: {dept.code}")
        
        # Find admin user for this department
        admin = db.query(models.User).filter(
            models.User.default_section_id == dept.id,
            models.User.role == "ADMIN_L1"
        ).first()
        
        if admin:
            print(f"   👤 Admin: {admin.username} ({admin.full_name})")
        else:
            print(f"   ⚠️  No admin user found")
        
        # Count budget rows for this department
        budget_count = db.query(models.BudgetRow).filter(
            models.BudgetRow.org_unit_id == dept.id
        ).count()
        print(f"   💰 Budget Lines: {budget_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Region 14 Audit and Verification Tool"
    )
    parser.add_argument('--trustees', action='store_true',
                       help='Show trustees and their admins')
    parser.add_argument('--users', action='store_true',
                       help='Show users only')
    parser.add_argument('--budget-summary', action='store_true',
                       help='Show budget summary only')
    parser.add_argument('--full', action='store_true',
                       help='Full audit (default)')
    
    args = parser.parse_args()
    
    # Default to full audit if no specific flag
    if not any([args.trustees, args.users, args.budget_summary]):
        args.full = True
    
    print("=" * 80)
    print("REGION 14 AUDIT TOOL")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        if args.trustees:
            show_trustees(db)
        elif args.users:
            audit_users(db)
        elif args.budget_summary:
            audit_budget_rows(db)
        else:  # Full audit
            audit_region_structure(db)
            audit_subsystem(db)
            audit_users(db)
            audit_budget_rows(db)
            audit_constraints(db)
            audit_integrity(db)
            
            print("\n" + "=" * 80)
            print("✓ AUDIT COMPLETE")
            print("=" * 80)
    
    except Exception as e:
        print(f"\n⚠️  ERROR during audit: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
