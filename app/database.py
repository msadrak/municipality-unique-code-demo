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


def _ensure_progress_statement_columns():
    """
    Lightweight compatibility migration for existing SQLite DBs.

    Older databases may have the `progress_statements` table without
    Sprint 3 columns. Since this project does not use Alembic yet,
    we patch missing columns at startup/import time.
    """
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        inspector = inspect(conn)
        if "progress_statements" not in inspector.get_table_names():
            return

        existing_columns = {
            col["name"] for col in inspector.get_columns("progress_statements")
        }

        alter_statements = []
        if "description" not in existing_columns:
            alter_statements.append(
                "ALTER TABLE progress_statements ADD COLUMN description VARCHAR"
            )
        if "period_start" not in existing_columns:
            alter_statements.append(
                "ALTER TABLE progress_statements ADD COLUMN period_start DATE"
            )
        if "period_end" not in existing_columns:
            alter_statements.append(
                "ALTER TABLE progress_statements ADD COLUMN period_end DATE"
            )

        for sql in alter_statements:
            conn.execute(text(sql))


_ensure_progress_statement_columns()
