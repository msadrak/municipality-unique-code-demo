"""
Reset default passwords for Region 14 section admins.
"""
import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app import models
from app.auth_utils import hash_password, verify_password

DEFAULT_ADMIN_PASSWORD = "Tehran@1403"
SECTION_ADMIN_USERNAMES = [
    "admin_road_14",
    "admin_elec_14",
    "admin_mech_14",
    "admin_civil_14",
    "admin_tech_14",
]


def reset_passwords(force: bool = True) -> None:
    db = SessionLocal()
    try:
        updated = 0
        skipped = 0
        missing = 0

        for username in SECTION_ADMIN_USERNAMES:
            user = db.query(models.User).filter(
                models.User.username == username
            ).first()

            if not user:
                print(f"[MISSING] {username}")
                missing += 1
                continue

            if not force and verify_password(DEFAULT_ADMIN_PASSWORD, user.password_hash or ""):
                print(f"[SKIP] {username} already uses default password")
                skipped += 1
                continue

            user.password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
            user.is_active = True
            updated += 1
            print(f"[RESET] {username}")

        db.commit()
        print(f"\nDone. reset={updated}, skipped={skipped}, missing={missing}")
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Force-reset Region 14 section admin passwords."
    )
    parser.add_argument(
        "--skip-unchanged",
        action="store_true",
        help="Skip users already using the default password.",
    )
    args = parser.parse_args()
    reset_passwords(force=not args.skip_unchanged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
