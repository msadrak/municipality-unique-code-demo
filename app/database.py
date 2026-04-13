"""
Database Configuration
======================

PostgreSQL connection via DATABASE_URL environment variable.
Connection pooling enabled for multi-worker production deployments.
Schema migrations are managed exclusively by Alembic.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Database URL (PostgreSQL only)
# ---------------------------------------------------------------------------
# Load project-level .env so uvicorn reload subprocesses get DATABASE_URL too.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required and must point to PostgreSQL.")

if not DATABASE_URL.startswith(("postgresql://", "postgresql+")):
    raise RuntimeError("DATABASE_URL must use a PostgreSQL SQLAlchemy URL.")


def _build_engine(database_url: str):
    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )


engine = _build_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("SELECT 1"))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Dependency — shared DB session generator
# ---------------------------------------------------------------------------
def get_db():
    """FastAPI dependency that yields a scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
