from typing import Dict

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Use SQLite for easier development/demo
SQLALCHEMY_DATABASE_URL = "sqlite:///./municipality_demo.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite in FastAPI
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _ensure_sqlite_columns(table_name: str, columns: Dict[str, str]) -> None:
    """
    Add missing columns to a SQLite table.

    This is a lightweight compatibility mechanism for environments that do not
    use Alembic migrations yet.
    """
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        inspector = inspect(conn)
        if table_name not in inspector.get_table_names():
            return

        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}

        for column_name, column_sql_type in columns.items():
            if column_name in existing_columns:
                continue
            conn.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} {column_sql_type}"
                )
            )


def _ensure_progress_statement_columns():
    """
    Lightweight compatibility migration for existing SQLite DBs.

    Older databases may have the `progress_statements` table without
    the generalized 4-stage workflow columns. Since this project does
    not use Alembic yet, we patch missing columns at startup/import time.
    """
    _ensure_sqlite_columns(
        table_name="progress_statements",
        columns={
            "description": "VARCHAR",
            "period_start": "DATE",
            "period_end": "DATE",
            # New generalized fields
            "originating_organ": "VARCHAR",
            "contract_ref_number": "VARCHAR",
            "contract_ref_date": "VARCHAR",
            "credit_ref_number": "VARCHAR",
            "credit_ref_amount": "BIGINT",
            "previous_statement_amount": "BIGINT DEFAULT 0",
            "insurance_deduction": "BIGINT DEFAULT 0",
            "tax_deduction": "BIGINT DEFAULT 0",
            "advance_payment_amount": "BIGINT DEFAULT 0",
            "other_deductions": "BIGINT DEFAULT 0",
            "price_index_base": "VARCHAR",
            "current_approval_level": "INTEGER DEFAULT 0",
            "template_data": "TEXT",  # JSON stored as TEXT in SQLite
            "rejected_by_id": "INTEGER",
            "rejection_reason": "VARCHAR",
            "rejected_at": "DATETIME",
        },
    )


def _ensure_transaction_v2_columns():
    """
    Add two-tier identification system columns to existing transactions table.
    """
    _ensure_sqlite_columns(
        table_name="transactions",
        columns={
            "tracking_number": "VARCHAR",
            "progress_statement_id": "INTEGER",
        },
    )


def _ensure_contractor_profile_columns():
    """
    Add onboarding/profile fields required by contractor authentication flow.
    """
    _ensure_sqlite_columns(
        table_name="contractors",
        columns={
            "corporate_id": "VARCHAR",
            "economic_code": "VARCHAR",
            "postal_code": "VARCHAR",
            "province": "VARCHAR",
            "city": "VARCHAR",
            "bank_name": "VARCHAR",
            "account_number": "VARCHAR",
            "iban": "VARCHAR",
        },
    )


_ensure_progress_statement_columns()
_ensure_transaction_v2_columns()
_ensure_contractor_profile_columns()

