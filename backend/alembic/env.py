"""
Alembic environment — reads DATABASE_URL from the app's config so migrations
always target the same database as the running app.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Ensure backend/ is on the path so 'app' can be imported ────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Load the app's DATABASE_URL ─────────────────────────────────────────────
# This triggers .env loading via config.py
from app.core.config import settings  # noqa: E402
from app.core.database import Base    # noqa: E402

# Import all models so Alembic can see them for autogenerate
from app.models.database import Client, APIKey, RefreshToken  # noqa: F401,E402

# ── Alembic boilerplate ─────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the sqlalchemy.url from alembic.ini with the real DATABASE_URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL if settings.DATABASE_URL else
    str(os.getenv("DATABASE_URL", f"sqlite:///./data/voicerag.db")))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
