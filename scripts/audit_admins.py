import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import User, Subsystem

def audit_admins():
    db = SessionLocal()
    try:
        print("\n🔍 Auditing Admin Users...")
        
        # 1. Fetch all potential admins
        # We look for role='admin' or username containing 'admin'
        users = db.query(User).filter(
            (User.role == 'admin') | (User.username.like('%admin%'))
        ).all()
        
        if not users:
            print("❌ No Admin users found!")
        else:
            print(f"✅ Found {len(users)} potential admin users:\n")
            print(f"{'ID':<5} {'Username':<20} {'Role':<15} {'Subsystem':<20} {'OrgUnit':<10}")
            print("-" * 75)
            
            for u in users:
                sub_info = str(u.managed_subsystem_ids) if hasattr(u, 'managed_subsystem_ids') and u.managed_subsystem_ids else "None"
                org_name = str(u.org_unit_id) if hasattr(u, 'org_unit_id') and u.org_unit_id else "Global"
                print(f"{u.id:<5} {u.username:<20} {u.role:<15} {sub_info:<20} {org_name:<10}")

        # 2. Check for Specific Hierarchy Levels
        print("\n🔍 Checking for Required Hierarchy Levels:")
        required_roles = {
            "Super Admin": {"username": "admin", "expected_role": "admin"},
            "Finance Admin": {"username": "admin_finance", "expected_role": "admin"}, # or similar
            "Urban Planning": {"username": "admin_urban", "expected_role": "admin"},
            "Inspector": {"username": "inspector", "expected_role": "inspector"},
        }
        
        found_levels = 0
        for label, criteria in required_roles.items():
            # Loose check: searching by mostly used conventions
            match = None
            for u in users:
                if criteria["username"] in u.username:
                    match = u
                    break
            
            if match:
                found_levels += 1
                print(f"  ✅ {label}: Found (ID={match.id}, Role={match.role})")
            else:
                print(f"  ❌ {label}: MISSING")
                
        print(f"\nAudit Result: Found {found_levels}/4 required levels.")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    audit_admins()
