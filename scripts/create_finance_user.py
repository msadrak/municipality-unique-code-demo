"""
Create Finance Test User
=========================

This script creates a finance_test user with:
1. Correct subsystem assignment (Treasury/Finance = ID 5)
2. Correct zone assignment (Region 1 = ID 1)

This also lists all subsystems to avoid guessing IDs.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import (
    User, 
    Subsystem, 
    UserSubsystemAccess,
    OrgUnit
)
import argon2


def list_all_subsystems(db: Session):
    """List all subsystems with their IDs."""
    print("\n" + "="*60)
    print("  ALL SUBSYSTEMS IN DATABASE")
    print("="*60)
    
    subsystems = db.query(Subsystem).order_by(Subsystem.id).all()
    
    print(f"\n{'ID':>4} | {'Code':25s} | Title")
    print("-" * 70)
    for sub in subsystems:
        print(f"{sub.id:>4} | {sub.code:25s} | {sub.title}")
    
    return subsystems


def create_finance_user(db: Session, username: str = "finance_test"):
    """Create a finance test user with Treasury subsystem access."""
    
    print("\n" + "="*60)
    print(f"  CREATING USER: {username}")
    print("="*60)
    
    # Step 1: Check if user already exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"\n⚠️  User '{username}' already exists (ID={existing.id})")
        print("   Updating their subsystem access instead...")
        user = existing
    else:
        # Create new user with Argon2 password
        ph = argon2.PasswordHasher()
        password_hash = ph.hash("test123")  # Simple test password
        
        user = User(
            username=username,
            password_hash=password_hash,
            full_name="کاربر آزمایشی مالی",  # Finance Test User
            role="USER",
            default_zone_id=1,  # Region 1
            default_dept_id=None,
            default_section_id=None,
            is_active=True
        )
        db.add(user)
        db.flush()  # Get the user ID
        print(f"\n✅ Created new user: {username} (ID={user.id})")
    
    # Step 2: Find Treasury/Finance subsystem
    # Based on diagnostic: TREASURY = ID 5 (سامانه خزانه‌داری)
    treasury = db.query(Subsystem).filter(Subsystem.code == "TREASURY").first()
    
    if not treasury:
        print("\n❌ ERROR: Treasury subsystem not found!")
        print("   Available subsystems are listed above.")
        db.rollback()
        return None
    
    print(f"\n✅ Found Treasury Subsystem:")
    print(f"   ID: {treasury.id}")
    print(f"   Code: {treasury.code}")
    print(f"   Title: {treasury.title}")
    
    # Step 3: Clear existing subsystem access and add Treasury
    db.query(UserSubsystemAccess).filter(
        UserSubsystemAccess.user_id == user.id
    ).delete()
    
    access = UserSubsystemAccess(
        user_id=user.id,
        subsystem_id=treasury.id
    )
    db.add(access)
    
    # Step 4: Verify zone assignment
    zone = db.query(OrgUnit).filter(OrgUnit.id == user.default_zone_id).first()
    
    print(f"\n✅ User Configuration:")
    print(f"   Username: {user.username}")
    print(f"   Full Name: {user.full_name}")
    print(f"   Role: {user.role}")
    print(f"   Zone: {zone.title if zone else 'N/A'} (ID={user.default_zone_id})")
    print(f"   Subsystem Access: {treasury.title} (ID={treasury.id})")
    print(f"   Password: test123")
    
    try:
        db.commit()
        print("\n✅ SUCCESS! User created/updated successfully.")
        return user
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        return None


def verify_user(db: Session, username: str):
    """Verify the user's complete profile."""
    print("\n" + "="*60)
    print("  USER VERIFICATION")
    print("="*60)
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        print(f"❌ User '{username}' not found!")
        return
    
    print(f"\n📋 User Profile: {user.username}")
    print("-" * 40)
    print(f"   ID: {user.id}")
    print(f"   Full Name: {user.full_name}")
    print(f"   Role: {user.role}")
    print(f"   Active: {user.is_active}")
    
    # Zone info
    if user.default_zone_id:
        zone = db.query(OrgUnit).filter(OrgUnit.id == user.default_zone_id).first()
        print(f"   Default Zone: {zone.title if zone else 'N/A'} (ID={user.default_zone_id})")
    else:
        print(f"   Default Zone: None")
    
    # Subsystem access
    print(f"\n📋 Subsystem Access:")
    accesses = db.query(UserSubsystemAccess).filter(
        UserSubsystemAccess.user_id == user.id
    ).all()
    
    if accesses:
        for access in accesses:
            sub = db.query(Subsystem).filter(Subsystem.id == access.subsystem_id).first()
            print(f"   - {sub.title if sub else 'Unknown'} (ID={access.subsystem_id})")
    else:
        print("   ⚠️  No subsystem access configured!")
    
    print("\n" + "="*60)
    print("  LOGIN CREDENTIALS")
    print("="*60)
    print(f"""
   Username: {username}
   Password: test123
   
   This user can access:
   - Treasury/Finance subsystem activities
   - Budget rows for Region 1 (org_unit_id=1)
   - Global budget rows (org_unit_id=NULL)
""")


def main():
    print("\n" + "👤" * 30)
    print("  FINANCE USER CREATION TOOL")
    print("👤" * 30)
    
    db = SessionLocal()
    try:
        # List all subsystems first
        list_all_subsystems(db)
        
        # Create finance user
        user = create_finance_user(db, "finance_test")
        
        if user:
            verify_user(db, "finance_test")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
