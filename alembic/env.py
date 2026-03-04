"""Alembic environment configuration for per-user SQLite databases.

This env.py handles the project's architecture where each Telegram user
has their own ``inventory_<chat_id>.db`` file plus a shared ``metadata.db``.

Running ``alembic upgrade head`` will:
1. Discover all ``.db`` files under the configured data directory.
2. Apply pending migrations to **every** database found.

For autogenerate (``alembic revision --autogenerate``), it uses the
``Item`` model (Base) against a single reference database.
"""
import os
import sys
from glob import glob
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine, pool
from alembic import context

# Ensure the project root is on sys.path so ``src`` is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database.models import Base, MetadataBase  # noqa: E402

# Alembic Config object — provides access to alembic.ini values.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate.  We track both the per-user
# inventory schema (Base) and the shared metadata schema (MetadataBase).
# Alembic will detect changes in either set of models.
target_metadata = Base.metadata


def _get_data_dir() -> Path:
    """Return the data directory containing all .db files.

    Respects ``DATABASE_URL`` from the environment if set, otherwise
    falls back to the ``sqlalchemy.url`` value from ``alembic.ini``.

    Returns:
        Path to the directory holding .db files.
    """
    db_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    raw_path = db_url.replace("sqlite:///", "")
    return Path(raw_path).parent


def _discover_databases() -> list[str]:
    """Find all SQLite database files that need migrating.

    Discovers ``inventory_*.db`` (per-user) files in the data directory.
    Metadata.db is excluded because it uses MetadataBase — a separate
    migration track could be added later if needed.

    Returns:
        List of ``sqlite:///`` connection URLs.
    """
    data_dir = _get_data_dir()
    db_files = sorted(glob(str(data_dir / "inventory_*.db")))
    # Also include the legacy inventory.db if it exists
    legacy = data_dir / "inventory.db"
    if legacy.exists() and str(legacy) not in db_files:
        db_files.insert(0, str(legacy))
    return [f"sqlite:///{p}" for p in db_files]


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emitting SQL without a live DB).

    Uses the fallback URL from alembic.ini.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against every discovered database.

    Iterates over all per-user databases and applies pending migrations
    to each one sequentially.
    """
    db_urls = _discover_databases()

    if not db_urls:
        # No databases found yet — run against the default URL so that
        # autogenerate still works on fresh checkouts.
        db_urls = [config.get_main_option("sqlalchemy.url")]

    for url in db_urls:
        print(f"  Migrating: {url}")
        engine = create_engine(url, poolclass=pool.NullPool)

        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,  # Required for SQLite ALTER TABLE
            )
            with context.begin_transaction():
                context.run_migrations()

        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

