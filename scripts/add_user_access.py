"""Add UserSubsystemAccess for test_user"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import User, Subsystem, UserSubsystemAccess

db = SessionLocal()
try:
    # Get test_user
    user = db.query(User).filter(User.username == 'test_user').first()
    if not user:
        print("test_user not found!")
        sys.exit(1)
    
    print(f"User: {user.username}, ID={user.id}")
    
    # Get Treasury subsystem (or first active one)
    treasury = db.query(Subsystem).filter(Subsystem.code == 'TREASURY').first()
    if not treasury:
        treasury = db.query(Subsystem).filter(Subsystem.is_active == True).first()
    
    if not treasury:
        print("No subsystem found!")
        sys.exit(1)
    
    print(f"Subsystem: {treasury.code} - {treasury.title}, ID={treasury.id}")
    
    # Check if access already exists
    existing = db.query(UserSubsystemAccess).filter(
        UserSubsystemAccess.user_id == user.id,
        UserSubsystemAccess.subsystem_id == treasury.id
    ).first()
    
    if existing:
        print("Access already exists!")
    else:
        access = UserSubsystemAccess(user_id=user.id, subsystem_id=treasury.id)
        db.add(access)
        db.commit()
        print(f"✅ Added {treasury.code} access for {user.username}")
    
    # List all accesses for this user
    accesses = db.query(UserSubsystemAccess).filter(
        UserSubsystemAccess.user_id == user.id
    ).all()
    print(f"\nUser has {len(accesses)} subsystem access(es):")
    for a in accesses:
        sub = db.query(Subsystem).filter(Subsystem.id == a.subsystem_id).first()
        print(f"  - {sub.title if sub else 'Unknown'}")

finally:
    db.close()
