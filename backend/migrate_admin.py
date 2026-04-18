"""
Migration: add is_admin and last_seen_at columns to clients table.
Run once: python migrate_admin.py
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import DATABASE_URL, engine
from sqlalchemy import text

def run():
    is_sqlite = DATABASE_URL.startswith("sqlite")
    with engine.connect() as conn:
        if is_sqlite:
            try:
                conn.execute(text("ALTER TABLE clients ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
                print("[migrate] Added is_admin column.")
            except Exception:
                print("[migrate] is_admin column already exists, skipping.")
            try:
                conn.execute(text("ALTER TABLE clients ADD COLUMN last_seen_at DATETIME"))
                print("[migrate] Added last_seen_at column.")
            except Exception:
                print("[migrate] last_seen_at column already exists, skipping.")
        else:
            # PostgreSQL
            conn.execute(text("""
                ALTER TABLE clients
                  ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                  ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
            """))
            print("[migrate] Columns added (PostgreSQL).")
        conn.commit()
    print("[migrate] Done.")

if __name__ == "__main__":
    run()
