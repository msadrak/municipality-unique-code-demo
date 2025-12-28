import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import User
from app.auth_utils import hash_password

def seed_admins():
    db = SessionLocal()
    try:
        print("\n🌱 Seeding strict 5-Level Organizational Hierarchy...")

        # Define 5 Levels of Organizational Hierarchy
        admins = [
            # Level 5: God Mode
            {
                "username": "admin_god",
                "role": "admin",
                "full_name": "طراح و راهبر سیستم",
                "admin_level": 5,
                "managed_subsystems": None
            },
            # Level 4: The Boss (Comptroller)
            {
                "username": "zihesab",
                "role": "admin",
                "full_name": "مدیر کل ذی‌حسابی و امور مالی",
                "admin_level": 4,
                "managed_subsystems": None
            },
            # Level 3: Zone/VP
            {
                "username": "admin_zone1",
                "role": "admin",
                "full_name": "معاونت منطقه ۱",
                "admin_level": 3,
                "managed_subsystems": None
            },
            # Level 2: Office
            {
                "username": "admin_office",
                "role": "admin",
                "full_name": "رئیس اداره برنامه ریزی",
                "admin_level": 2,
                "managed_subsystems": None
            },
            # Level 1: Section
            {
                "username": "admin_section",
                "role": "admin",
                "full_name": "مسئول قسمت بودجه",
                "admin_level": 1,
                "managed_subsystems": None
            }
        ]
        
        # ...

        for admin_data in admins:
            user = db.query(User).filter(User.username == admin_data["username"]).first()
            hashed_pw = hash_password("admin123")
            
            if not user:
                print(f"Creating {admin_data['username']} (Level {admin_data['admin_level']})...")
                user = User(
                    username=admin_data["username"],
                    full_name=admin_data["full_name"],
                    role=admin_data["role"],
                    password_hash=hashed_pw, 
                    admin_level=admin_data["admin_level"],
                    managed_subsystem_ids=None, # Explicitly null
                    is_active=True
                )
                db.add(user)
            else:
                print(f"Updating {admin_data['username']} (Level {admin_data['admin_level']})...")
                user.full_name = admin_data["full_name"]
                user.role = admin_data["role"]
                user.admin_level = admin_data["admin_level"]
                user.managed_subsystem_ids = None 
                user.password_hash = hashed_pw # Force update password too
            
            db.commit()

        print("✅ 5-Level Hierarchy (God -> Zihesab -> Zone -> Office -> Section) Seeded.")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admins()
