"""
Seed script: Create/Update test users with proper Argon2 password hashes.

This script is IDEMPOTENT:
- If users exist, updates their passwords with fresh Argon2 hashes
- If users don't exist, creates them

Usage:
    python seed_users.py
"""

import sys
sys.path.insert(0, '.')

from app.database import SessionLocal, engine
from app.models import Base, User, OrgUnit
from app.auth_utils import hash_password

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Test users to seed
TEST_USERS = [
    {
        "username": "test_user",
        "password": "user123",
        "full_name": "کاربر آزمایشی",
        "role": "user",
    },
    {
        "username": "admin",
        "password": "admin123",
        "full_name": "مدیر سیستم",
        "role": "admin",
    },
]


def seed_users():
    print("=" * 60)
    print("SEED USERS - Argon2 Password Hashing")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get default org units for users
        zone = db.query(OrgUnit).filter(OrgUnit.org_type == "zone").first()
        section = db.query(OrgUnit).filter(OrgUnit.org_type == "section").first()
        
        for user_data in TEST_USERS:
            username = user_data["username"]
            password = user_data["password"]
            
            # Check if user exists
            existing = db.query(User).filter(User.username == username).first()
            
            # Generate fresh Argon2 hash
            new_hash = hash_password(password)
            
            if existing:
                # UPDATE: Fix existing user with fresh Argon2 hash
                print(f"🔄 Updating user: {username}")
                print(f"   Old hash type: {'Argon2' if existing.password_hash.startswith('$argon2') else 'Legacy/SHA256'}")
                existing.password_hash = new_hash
                existing.full_name = user_data["full_name"]
                existing.role = user_data["role"]
                existing.is_active = True
                
                # Update org units if available
                if zone:
                    existing.default_zone_id = zone.id
                if section:
                    existing.default_section_id = section.id
                    
                print(f"   ✅ Password updated to Argon2")
            else:
                # CREATE: New user with Argon2 hash
                print(f"➕ Creating user: {username}")
                new_user = User(
                    username=username,
                    password_hash=new_hash,
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    is_active=True,
                    default_zone_id=zone.id if zone else None,
                    default_section_id=section.id if section else None,
                )
                db.add(new_user)
                print(f"   ✅ User created with Argon2 hash")
        
        db.commit()
        print("\n" + "=" * 60)
        print("✅ All users seeded successfully!")
        print(f"   Zone assigned: {zone.title if zone else 'None'}")
        print(f"   Section assigned: {section.title if section else 'None'}")
        print("=" * 60)
        
        # Show login credentials
        print("\n📋 Login Credentials:")
        for u in TEST_USERS:
            print(f"   Username: {u['username']} | Password: {u['password']} | Role: {u['role']}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
