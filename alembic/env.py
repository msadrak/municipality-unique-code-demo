"""
Alembic Environment Configuration
=================================

This module configures the Alembic migration environment for the
Municipality ERP application. It resolves a PostgreSQL DATABASE_URL
before importing application modules.

All SQLAlchemy models are imported through ``app.models``, which
registers every table on ``Base.metadata`` before Alembic inspects it.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Alembic Config object - provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

def _resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not database_url:
        raise RuntimeError(
            "Alembic requires a PostgreSQL DATABASE_URL. "
            "Set DATABASE_URL or sqlalchemy.url in alembic.ini."
        )
    if not database_url.startswith(("postgresql://", "postgresql+")):
        raise RuntimeError("Alembic requires a PostgreSQL SQLAlchemy URL.")
    return database_url


DATABASE_URL = _resolve_database_url()
os.environ.setdefault("DATABASE_URL", DATABASE_URL)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# ---------------------------------------------------------------------------
# Make sure the `app` package is importable from the project root.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object used for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
