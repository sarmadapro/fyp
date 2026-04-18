"""
Create an admin account.
Usage:  python create_admin.py admin@example.com secretpass123
        python create_admin.py  (will prompt)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import migrate_admin          # ensure columns exist first
migrate_admin.run()

from app.core.database import SessionLocal
from app.models.database import Client, APIKey
from app.services.auth_service import hash_password, get_client_by_email

def create_admin(email: str, password: str, company: str = "Admin"):
    db = SessionLocal()
    try:
        existing = get_client_by_email(db, email)
        if existing:
            existing.is_admin = True
            existing.is_active = True
            db.commit()
            print(f"[admin] Promoted existing user '{email}' to admin.")
            return

        client = Client(
            email=email.lower().strip(),
            hashed_password=hash_password(password),
            company_name=company,
            full_name="Administrator",
            is_active=True,
            is_email_verified=True,
            is_admin=True,
        )
        db.add(client)
        db.flush()

        full_key, prefix, key_hash = APIKey.generate_key()
        db.add(APIKey(client_id=client.id, name="Admin Key", key_prefix=prefix, key_hash=key_hash))
        db.commit()

        print(f"[admin] Admin account created: {email}")
        print(f"[admin] API Key (save this): {full_key}")
    finally:
        db.close()

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 2:
        email, password = args[0], args[1]
    else:
        email    = input("Admin email: ").strip()
        password = input("Admin password: ").strip()
    create_admin(email, password)
