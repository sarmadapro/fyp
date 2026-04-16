"""
Database configuration — SQLAlchemy + SQLite.
Zero-dependency setup: just works out of the box.
Upgrade to PostgreSQL by changing DATABASE_URL.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Database file location
_DB_DIR = Path(os.getenv("DB_DIR", "./data"))
_DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DB_DIR / 'voicerag.db'}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Safe to call multiple times."""
    from app.models.database import Client, APIKey  # noqa: F401
    Base.metadata.create_all(bind=engine)
