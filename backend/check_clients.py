from app.core.database import engine
from app.models.database import Client
from sqlalchemy.orm import Session

with Session(engine) as db:
    clients = db.query(Client).all()
    for c in clients:
        verified = getattr(c, 'is_verified', 'N/A')
        active = getattr(c, 'is_active', 'N/A')
        print(f"ID: {c.id} | Email: {c.email} | Active: {active} | Verified: {verified}")
    print(f"Total clients: {len(clients)}")
