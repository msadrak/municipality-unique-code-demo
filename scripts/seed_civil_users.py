from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.auth_utils import hash_password
from app.models.enums import UserRole

DEFAULT_PASSWORD = "password123"

CIVIL_USERS: tuple[dict[str, str], ...] = (
    {
        "email": "civil@test.com",
        "role": UserRole.CIVIL_MANAGER.value,
        "full_name": "مدیر عمران منطقه",
    },
    {
        "email": "tender@test.com",
        "role": UserRole.TENDERING_OFFICER.value,
        "full_name": "مسئول مناقصات",
    },
    {
        "email": "contract@test.com",
        "role": UserRole.CONTRACTS_OFFICER.value,
        "full_name": "مسئول قراردادها",
    },
    {
        "email": "supervisor@test.com",
        "role": UserRole.SUPERVISOR.value,
        "full_name": "ناظر مقیم",
    },
    {
        "email": "commission@test.com",
        "role": UserRole.DELIVERY_COMMISSION.value,
        "full_name": "دبیر کمیسیون",
    },
    {
        "email": "contractor@test.com",
        "role": UserRole.CONTRACTOR.value,
        "full_name": "شرکت پیمانکاری راه و باند",
    },
    {
        "email": "finance@test.com",
        "role": UserRole.FINANCE_MANAGER.value,
        "full_name": "ذی‌حساب عمران",
    },
)


def resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        raise RuntimeError("DATABASE_URL is not set and .env is missing.")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DATABASE_URL":
            return value.strip().strip("\"'")

    raise RuntimeError("DATABASE_URL is not set in the environment or .env.")


def load_users_table(database_url: str) -> tuple[object, Table]:
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    metadata = MetaData()
    users = Table("users", metadata, autoload_with=engine)
    return engine, users


def assert_required_columns(users: Table) -> None:
    required = {"username", "password_hash", "full_name", "role"}
    missing = sorted(column for column in required if column not in users.c)
    if missing:
        raise RuntimeError(f"users table is missing required columns: {', '.join(missing)}")


def build_values(users: Table, seed_user: dict[str, str], password_hash: str) -> dict[str, object]:
    values: dict[str, object] = {
        "username": seed_user["email"],
        "password_hash": password_hash,
        "full_name": seed_user["full_name"],
        "role": seed_user["role"],
    }

    optional_fields: dict[str, object] = {
        "email": seed_user["email"],
        "is_active": True,
        "failed_attempts": 0,
        "locked_until": None,
        "region_name": None,
    }
    for field_name, field_value in optional_fields.items():
        if field_name in users.c:
            values[field_name] = field_value

    if "created_at" in users.c:
        values["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    return values


def print_summary(rows: list[dict[str, str]]) -> None:
    headers = ("Status", "Email", "Role", "Name")
    widths = {
        "Status": max(len("Status"), *(len(row["status"]) for row in rows)),
        "Email": max(len("Email"), *(len(row["email"]) for row in rows)),
        "Role": max(len("Role"), *(len(row["role"]) for row in rows)),
        "Name": max(len("Name"), *(len(row["full_name"]) for row in rows)),
    }

    border = "+-" + "-+-".join("-" * widths[header] for header in headers) + "-+"
    header_row = "| " + " | ".join(header.ljust(widths[header]) for header in headers) + " |"

    print(border)
    print(header_row)
    print(border)
    for row in rows:
        print(
            "| "
            + " | ".join(
                (
                    row["status"].ljust(widths["Status"]),
                    row["email"].ljust(widths["Email"]),
                    row["role"].ljust(widths["Role"]),
                    row["full_name"].ljust(widths["Name"]),
                )
            )
            + " |"
        )
    print(border)


def seed_users() -> None:
    database_url = resolve_database_url()
    engine, users = load_users_table(database_url)
    assert_required_columns(users)

    usernames = [item["email"] for item in CIVIL_USERS]
    summary_rows: list[dict[str, str]] = []

    with engine.begin() as connection:
        existing = set(
            connection.execute(
                select(users.c.username).where(users.c.username.in_(usernames))
            ).scalars()
        )

        for seed_user in CIVIL_USERS:
            password_hash = hash_password(DEFAULT_PASSWORD)
            values = build_values(users, seed_user, password_hash)

            insert_stmt = pg_insert(users).values(**values)
            update_columns = {
                column_name: getattr(insert_stmt.excluded, column_name)
                for column_name in values
                if column_name != "created_at"
            }

            connection.execute(
                insert_stmt.on_conflict_do_update(
                    index_elements=[users.c.username],
                    set_=update_columns,
                )
            )

            summary_rows.append(
                {
                    "status": "updated" if seed_user["email"] in existing else "created",
                    "email": seed_user["email"],
                    "role": seed_user["role"],
                    "full_name": seed_user["full_name"],
                }
            )

    print("")
    print("Civil test users seeded successfully.")
    print(f"Default password: {DEFAULT_PASSWORD}")
    print_summary(summary_rows)


if __name__ == "__main__":
    seed_users()
