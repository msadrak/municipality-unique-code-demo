"""
Create or update an approval-capable manager user for contract workflow tests.

Usage:
    python scripts/create_manager.py
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is importable when script runs from /scripts
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.auth_utils import hash_password
from app.database import SessionLocal
from app.models import OrgUnit, User


USERNAME = "manager_road_14"
PASSWORD = "admin"
FULL_NAME = "Road Manager 14"
ROLE = "ADMIN_L2"
ADMIN_LEVEL = 2


def _safe_text(value: object) -> str:
    """Render text safely on legacy Windows consoles."""
    text = str(value) if value is not None else "None"
    return text.encode("ascii", errors="replace").decode("ascii")


def _find_default_zone(db) -> Optional[OrgUnit]:
    """Prefer Region/Zone code 14, then fallback to first zone-like record."""
    zone = db.query(OrgUnit).filter(OrgUnit.code == "14").first()
    if zone:
        return zone
    return db.query(OrgUnit).filter(OrgUnit.org_type == "zone").first()


def main() -> int:
    db = SessionLocal()
    try:
        zone = _find_default_zone(db)

        user = db.query(User).filter(User.username == USERNAME).first()
        if user:
            user.password_hash = hash_password(PASSWORD)
            user.full_name = FULL_NAME
            user.role = ROLE
            user.admin_level = ADMIN_LEVEL
            user.is_active = True
            if zone:
                user.default_zone_id = zone.id
            action = "updated"
        else:
            user = User(
                username=USERNAME,
                password_hash=hash_password(PASSWORD),
                full_name=FULL_NAME,
                role=ROLE,
                admin_level=ADMIN_LEVEL,
                default_zone_id=zone.id if zone else None,
                is_active=True,
            )
            db.add(user)
            action = "created"

        db.commit()
        db.refresh(user)

        print("=" * 68)
        print("MANAGER USER READY")
        print("=" * 68)
        print(f"Status    : {action}")
        print(f"Username  : {USERNAME}")
        print(f"Password  : {PASSWORD}")
        print(f"Role      : {user.role}")
        print(f"Level     : {user.admin_level}")
        print(f"User ID   : {user.id}")
        print(f"Active    : {user.is_active}")
        print(f"Zone      : {_safe_text(zone.title if zone else 'None')}")
        print("-" * 68)
        print("Contract transition guard note:")
        print("  app/routers/contracts.py uses _require_auth() only.")
        print("  Any authenticated user passes this guard, including this user.")
        print("=" * 68)
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {type(exc).__name__}: {_safe_text(exc)}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
