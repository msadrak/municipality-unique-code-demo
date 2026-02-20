"""
Seed Admin Hierarchy - Create 4-level approval users
=====================================================

Creates ADMIN_L1 through ADMIN_L4 users with proper organizational assignments
for testing the multi-level approval workflow.

Usage:
    python scripts/seed_admin_hierarchy.py
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, engine
from app import models
from app.auth_utils import hash_password


ADMIN_USERS = [
    {
        "username": "manager_l1",
        "password": "manager1",
        "full_name": "مسئول قسمت عمرانی",
        "role": "ADMIN_L1",
        "admin_level": 1,
        "dept_code": "10",       # اداره مالی
        "section_code": "101",   # قسمت حسابداری
    },
    {
        "username": "manager_l2",
        "password": "manager2",
        "full_name": "رئیس اداره خدمات",
        "role": "ADMIN_L2",
        "admin_level": 2,
        "dept_code": "10",
    },
    {
        "username": "manager_l3",
        "password": "manager3",
        "full_name": "مدیر حوزه منطقه ۱",
        "role": "ADMIN_L3",
        "admin_level": 3,
    },
    {
        "username": "manager_l4",
        "password": "manager4",
        "full_name": "ذی‌حساب شهرداری",
        "role": "ADMIN_L4",
        "admin_level": 4,
    },
]


def seed_admin_hierarchy():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Resolve the default zone (first ZONE-type org unit)
        zone = (
            db.query(models.OrgUnit)
            .filter(models.OrgUnit.org_type == "ZONE")
            .first()
        )
        if not zone:
            print("[!] No ZONE org unit found. Creating a default zone...")
            zone = models.OrgUnit(title="منطقه ۱", code="01", org_type="ZONE")
            db.add(zone)
            db.commit()
            db.refresh(zone)

        dept_map: dict[str, models.OrgUnit] = {}
        section_map: dict[str, models.OrgUnit] = {}

        for dept in db.query(models.OrgUnit).filter(
            models.OrgUnit.org_type == "DEPT",
            models.OrgUnit.parent_id == zone.id,
        ):
            dept_map[dept.code] = dept

        for sec in db.query(models.OrgUnit).filter(
            models.OrgUnit.org_type == "SECTION",
        ):
            section_map[sec.code] = sec

        print("=" * 60)
        print("  ADMIN HIERARCHY SEEDER")
        print("=" * 60)
        print(f"  Zone: {zone.title} (id={zone.id})")
        print()

        created = 0
        skipped = 0

        for spec in ADMIN_USERS:
            existing = (
                db.query(models.User)
                .filter(models.User.username == spec["username"])
                .first()
            )
            if existing:
                print(f"  [SKIP] {spec['username']} already exists (id={existing.id})")
                skipped += 1
                continue

            dept = dept_map.get(spec.get("dept_code", "")) if spec.get("dept_code") else None
            section = section_map.get(spec.get("section_code", "")) if spec.get("section_code") else None

            user = models.User(
                username=spec["username"],
                password_hash=hash_password(spec["password"]),
                full_name=spec["full_name"],
                role=spec["role"],
                admin_level=spec["admin_level"],
                default_zone_id=zone.id,
                default_dept_id=dept.id if dept else None,
                default_section_id=section.id if section else None,
                is_active=True,
            )
            db.add(user)
            created += 1

        db.commit()

        print()
        print("-" * 60)
        print("  CREDENTIALS")
        print("-" * 60)
        for spec in ADMIN_USERS:
            level_label = {
                1: "قسمت (Section)",
                2: "اداره (Office)",
                3: "حوزه (Zone)",
                4: "ذی‌حساب (Finance)",
            }.get(spec["admin_level"], "?")

            print(f"  L{spec['admin_level']} | {level_label}")
            print(f"     Username: {spec['username']}")
            print(f"     Password: {spec['password']}")
            print(f"     Role:     {spec['role']}")
            print()

        print("-" * 60)
        print(f"  Created: {created}  |  Skipped: {skipped}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_hierarchy()
