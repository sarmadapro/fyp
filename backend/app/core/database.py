"""
Database configuration — SQLAlchemy with SQLite (dev) or PostgreSQL (production).

Set DATABASE_URL in .env to switch:
  SQLite:     sqlite:///./data/voicerag.db   (default, zero-config)
  PostgreSQL: postgresql://user:pass@host:5432/voicerag
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

# ── URL resolution ──────────────────────────────────────────────────────────
_DB_DIR = Path(os.getenv("DB_DIR", "./data"))
_DB_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_DB_DIR / 'voicerag.db'}"
)

# Normalize Heroku/Azure-style "postgres://" → "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── Engine ──────────────────────────────────────────────────────────────────
_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"echo": False}

if _is_sqlite:
    # SQLite: check_same_thread=False required for FastAPI's async context
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: use NullPool in async context to avoid connection leaks
    # (can swap to AsyncSession + asyncpg later for full async support)
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base ────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ──────────────────────────────────────────────────────

def get_db():
    """Yields a DB session. Always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Init ────────────────────────────────────────────────────────────────────

def init_db():
    """
    Create all tables from ORM models.
    Safe to call multiple times (CREATE TABLE IF NOT EXISTS semantics).
    In production, prefer Alembic migrations over this.
    """
    # Import models so they register with Base.metadata
    from app.models.database import Client, APIKey, RefreshToken  # noqa: F401
    Base.metadata.create_all(bind=engine)
    db_type = "SQLite" if _is_sqlite else "PostgreSQL"
    print(f"[DB] Tables initialized ({db_type}): {DATABASE_URL[:40]}...")
