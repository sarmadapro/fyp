"""
Database migration script — adds new columns and tables to an existing voicerag.db.

Safe to run multiple times (idempotent).  Does NOT delete any existing data.

Usage:
    python migrate_db.py
"""

import os
import sys
import sqlite3
from pathlib import Path

# ── Locate the database ──────────────────────────────────────────────────────
DB_PATH = Path(os.getenv("DB_PATH", "./data/voicerag.db"))

if not DB_PATH.exists():
    print(f"[migrate] No database found at {DB_PATH} — nothing to migrate.")
    sys.exit(0)

print(f"[migrate] Migrating: {DB_PATH.resolve()}")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()


# ── Helpers ──────────────────────────────────────────────────────────────────

def column_exists(table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def table_exists(table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def add_column(table: str, column: str, definition: str):
    if not column_exists(table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  [+] {table}.{column}")
    else:
        print(f"  [=] {table}.{column} already exists")


# ── Migrate clients table ────────────────────────────────────────────────────
print("\n[1/3] Checking clients table...")

add_column("clients", "is_email_verified",             "BOOLEAN DEFAULT 0")
add_column("clients", "email_verification_token",      "TEXT")
add_column("clients", "email_verification_expires_at", "DATETIME")
add_column("clients", "password_reset_token",          "TEXT")
add_column("clients", "password_reset_expires_at",     "DATETIME")

# Add indexes for the new columns (safe to ignore if they already exist)
try:
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_clients_email_verification_token "
        "ON clients (email_verification_token)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_clients_password_reset_token "
        "ON clients (password_reset_token)"
    )
    print("  [+] indexes on verification/reset token columns")
except Exception as e:
    print(f"  [!] index creation skipped: {e}")

# ── Create refresh_tokens table ──────────────────────────────────────────────
print("\n[2/3] Checking refresh_tokens table...")

if not table_exists("refresh_tokens"):
    cursor.execute("""
        CREATE TABLE refresh_tokens (
            id          TEXT PRIMARY KEY,
            client_id   TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            token_hash  TEXT NOT NULL,
            expires_at  DATETIME NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            revoked     BOOLEAN DEFAULT 0,
            user_agent  TEXT,
            ip_address  TEXT
        )
    """)
    cursor.execute(
        "CREATE UNIQUE INDEX ix_refresh_tokens_token_hash ON refresh_tokens (token_hash)"
    )
    cursor.execute(
        "CREATE INDEX ix_refresh_tokens_client_id ON refresh_tokens (client_id)"
    )
    print("  [+] refresh_tokens table created")
else:
    print("  [=] refresh_tokens table already exists")

# ── Mark existing clients as email-verified ──────────────────────────────────
print("\n[3/3] Marking pre-existing accounts as email-verified...")

cursor.execute(
    "UPDATE clients SET is_email_verified = 1 WHERE is_email_verified = 0"
)
updated = cursor.rowcount
print(f"  [+] {updated} existing account(s) marked as verified")

# ── Commit & close ───────────────────────────────────────────────────────────
conn.commit()
conn.close()

print("\n[migrate] Done. Database is up to date.")
