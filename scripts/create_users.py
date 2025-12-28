# Quick user creation script
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import User, OrgUnit
from app.auth_utils import hash_password

db = SessionLocal()

# Get a zone and section for defaults
zone = db.query(OrgUnit).filter(OrgUnit.org_type == 'zone').first()
section = db.query(OrgUnit).filter(OrgUnit.org_type == 'section').first()

print(f"Zone: {zone.title if zone else 'None'}")
print(f"Section: {section.title if section else 'None'}")

# Check if admin already exists
existing_admin = db.query(User).filter(User.username == 'admin').first()
if existing_admin:
    print("Admin already exists, skipping...")
else:
    admin = User(
        username='admin',
        password_hash=hash_password('admin123'),
        full_name='مدیر سیستم',
        role='admin',
        default_zone_id=zone.id if zone else None,
        default_section_id=section.id if section else None,
        is_active=True
    )
    db.add(admin)
    print("Created: admin/admin123")

# Check if test_user already exists
existing_user = db.query(User).filter(User.username == 'test_user').first()
if existing_user:
    print("test_user already exists, skipping...")
else:
    test_user = User(
        username='test_user',
        password_hash=hash_password('user123'),
        full_name='کاربر تست',
        role='user',
        default_zone_id=zone.id if zone else None,
        default_section_id=section.id if section else None,
        is_active=True
    )
    db.add(test_user)
    print("Created: test_user/user123")

db.commit()
db.close()
print("✅ Done!")
