"""
Authentication service — JWT tokens + password hashing.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.models.database import Client

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "voicerag-dev-secret-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def register_client(db: Session, email: str, password: str, company_name: str, full_name: str = "") -> Client:
    """Register a new client. Raises ValueError if email exists."""
    existing = db.query(Client).filter(Client.email == email).first()
    if existing:
        raise ValueError("An account with this email already exists.")

    client = Client(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        company_name=company_name.strip(),
        full_name=full_name.strip(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    logger.info(f"[Auth] New client registered: {client.email} (id={client.id})")
    return client


def authenticate_client(db: Session, email: str, password: str) -> Optional[Client]:
    """Authenticate a client by email + password. Returns None if invalid."""
    client = db.query(Client).filter(Client.email == email.lower().strip()).first()
    if not client:
        return None
    if not verify_password(password, client.hashed_password):
        return None
    if not client.is_active:
        return None
    return client


def get_client_by_id(db: Session, client_id: str) -> Optional[Client]:
    return db.query(Client).filter(Client.id == client_id).first()
