from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import get_password_hash
from app.database import SessionLocal, engine
from app.models import Base, User, UserRole
from app.utils.constants import AUTHORIZED_REGIONS

DEFAULT_PASSWORD = "123456"
CIVIL_DEMO_PASSWORD = "password123"


def ensure_user_schema() -> None:
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "region_name" in existing_columns:
        return

    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE users ADD COLUMN region_name VARCHAR(128)")


def build_seed_payload() -> list[dict[str, str | None]]:
    region_users = [
        {
            "username": region_name,
            "full_name": region_name,
            "role": UserRole.REGION_USER.value,
            "region_name": region_name,
        }
        for region_name in AUTHORIZED_REGIONS
    ]

    special_users = [
        {
            "username": "admin@test.com",
            "full_name": "Demo Administrator",
            "role": UserRole.ADMIN.value,
            "region_name": None,
            "password": CIVIL_DEMO_PASSWORD,
        },
        {
            "username": "civil@test.com",
            "full_name": "Civil Demo Manager",
            "role": UserRole.CIVIL_MANAGER.value,
            "region_name": None,
            "password": CIVIL_DEMO_PASSWORD,
        },
        {
            "username": "supervisor.demo@municipality.local",
            "full_name": "Civil Demo Supervisor",
            "role": UserRole.SUPERVISOR.value,
            "region_name": None,
            "password": CIVIL_DEMO_PASSWORD,
        },
        {
            "username": "hr_admin@test.com",
            "full_name": "HR Volume Contracts Admin",
            "role": UserRole.HR_ADMIN.value,
            "region_name": None,
            "password": CIVIL_DEMO_PASSWORD,
        },
        {
            "username": "finance_manager@test.com",
            "full_name": "Finance Volume Contracts Manager",
            "role": UserRole.FINANCE_MANAGER.value,
            "region_name": None,
            "password": CIVIL_DEMO_PASSWORD,
        },
        {
            "username": "yekta_admin@test.com",
            "full_name": "Yekta Code Admin",
            "role": "YEKTA_ADMIN",
            "region_name": None,
            "password": CIVIL_DEMO_PASSWORD,
        },
        {
            "username": "cleaning_contractor@test.com",
            "full_name": "Cleaning Services Contractor",
            "role": UserRole.CONTRACTOR.value,
            "region_name": None,
            "password": CIVIL_DEMO_PASSWORD,
        },
        {
            "username": "niroumand",
            "full_name": "نیرومند",
            "role": UserRole.SECURITY_AGGREGATOR.value,
            "region_name": None,
        },
        {
            "username": "contractor",
            "full_name": "پیمانکار",
            "role": UserRole.CONTRACTOR.value,
            "region_name": None,
        },
        {
            "username": "bahadori",
            "full_name": "بهادری",
            "role": "YEKTA_ADMIN",
            "region_name": None,
        },
    ]

    return [*region_users, *special_users]


def seed_users() -> None:
    ensure_user_schema()

    seed_payload = build_seed_payload()
    created_count = 0
    skipped_count = 0

    db = SessionLocal()
    try:
        for item in seed_payload:
            username = str(item["username"]).strip()
            password = str(item.get("password") or DEFAULT_PASSWORD)
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                existing_user.hashed_password = get_password_hash(password)
                existing_user.full_name = item["full_name"]
                existing_user.role = str(item["role"])
                existing_user.region_name = item["region_name"]
                existing_user.is_active = True
                existing_user.failed_attempts = 0
                existing_user.locked_until = None
                skipped_count += 1
                print(f"UPDATE  {username}")
                continue

            db.add(
                User(
                    username=username,
                    hashed_password=get_password_hash(password),
                    full_name=item["full_name"],
                    role=str(item["role"]),
                    region_name=item["region_name"],
                    is_active=True,
                    failed_attempts=0,
                )
            )
            created_count += 1
            print(f"CREATE  {username}")

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("-" * 72)
    print(f"Created: {created_count}")
    print(f"Updated: {skipped_count}")
    print(f"Total target users: {len(seed_payload)}")
    print(f"Default password: {DEFAULT_PASSWORD}")
    print("Demo logins:")
    print(f"  admin@test.com / {CIVIL_DEMO_PASSWORD}")
    print(f"  civil@test.com / {CIVIL_DEMO_PASSWORD}")
    print(f"  supervisor.demo@municipality.local / {CIVIL_DEMO_PASSWORD}")
    print(f"  hr_admin@test.com / {CIVIL_DEMO_PASSWORD}")
    print(f"  finance_manager@test.com / {CIVIL_DEMO_PASSWORD}")
    print(f"  yekta_admin@test.com / {CIVIL_DEMO_PASSWORD}")
    print(f"  bahadori / {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    seed_users()
