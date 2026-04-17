"""
Authentication service.

Handles:
  - Password hashing / verification
  - JWT access token (short-lived, 30 min)
  - JWT refresh token (long-lived, 7 days, stored hashed in DB)
  - Client registration / login
  - Email verification
  - Password reset
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import Client, RefreshToken

logger = logging.getLogger(__name__)

# ── Password hashing ────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ─────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = _utcnow() + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token. Returns None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


# ── Refresh token helpers ────────────────────────────────────────────────────

def create_refresh_token(
    db: Session,
    client_id: str,
    user_agent: str = "",
    ip_address: str = "",
) -> str:
    """
    Generate a secure refresh token, store its hash in the DB, return the raw token.
    The raw token is sent to the client (HTTP-only cookie recommended).
    """
    raw, token_hash = RefreshToken.generate()
    expires_at = _utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    rt = RefreshToken(
        client_id=client_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent[:512] if user_agent else None,
        ip_address=ip_address[:45] if ip_address else None,
    )
    db.add(rt)
    db.commit()
    logger.info(f"[Auth] Refresh token created for client {client_id}")
    return raw


def validate_and_rotate_refresh_token(
    db: Session,
    raw_token: str,
    user_agent: str = "",
    ip_address: str = "",
) -> tuple[Optional[Client], Optional[str]]:
    """
    Validate a refresh token, revoke the old one, and issue a new one (rotation).
    Returns: (client, new_raw_refresh_token) or (None, None) if invalid.
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = _utcnow()

    rt = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > now,
        )
        .first()
    )

    if not rt:
        logger.warning("[Auth] Invalid or expired refresh token presented")
        return None, None

    client = db.query(Client).filter(Client.id == rt.client_id).first()
    if not client or not client.is_active:
        rt.revoked = True
        db.commit()
        return None, None

    # Revoke the old token
    rt.revoked = True
    db.commit()

    # Issue a new token (rotation)
    new_raw = create_refresh_token(db, client.id, user_agent, ip_address)
    return client, new_raw


def revoke_all_refresh_tokens(db: Session, client_id: str) -> int:
    """Revoke all active refresh tokens for a client (logout-all)."""
    count = (
        db.query(RefreshToken)
        .filter(RefreshToken.client_id == client_id, RefreshToken.revoked == False)
        .update({"revoked": True})
    )
    db.commit()
    logger.info(f"[Auth] Revoked {count} refresh tokens for client {client_id}")
    return count


# ── Email verification ───────────────────────────────────────────────────────

def generate_verification_token() -> str:
    """Generate a URL-safe random token."""
    return secrets.token_urlsafe(32)


def set_email_verification_token(db: Session, client: Client) -> str:
    """Attach a new email verification token to the client. Returns the raw token."""
    token = generate_verification_token()
    client.email_verification_token = token
    client.email_verification_expires_at = _utcnow() + timedelta(hours=24)
    db.commit()
    return token


def verify_email_token(db: Session, token: str) -> Optional[Client]:
    """
    Find the client with this verification token, mark email as verified.
    Returns the client on success, None if token is invalid/expired.
    """
    now = _utcnow()
    client = (
        db.query(Client)
        .filter(
            Client.email_verification_token == token,
            Client.email_verification_expires_at > now,
            Client.is_email_verified == False,
        )
        .first()
    )
    if not client:
        return None

    client.is_email_verified = True
    client.email_verification_token = None
    client.email_verification_expires_at = None
    db.commit()
    logger.info(f"[Auth] Email verified for client {client.email}")
    return client


# ── Password reset ───────────────────────────────────────────────────────────

def set_password_reset_token(db: Session, client: Client) -> str:
    """Attach a password reset token. Returns the raw token."""
    token = generate_verification_token()
    client.password_reset_token = token
    client.password_reset_expires_at = _utcnow() + timedelta(hours=1)
    db.commit()
    return token


def reset_password_with_token(db: Session, token: str, new_password: str) -> Optional[Client]:
    """
    Find the client with this reset token, update their password.
    Returns the client on success, None if token invalid/expired.
    """
    now = _utcnow()
    client = (
        db.query(Client)
        .filter(
            Client.password_reset_token == token,
            Client.password_reset_expires_at > now,
        )
        .first()
    )
    if not client:
        return None

    client.hashed_password = hash_password(new_password)
    client.password_reset_token = None
    client.password_reset_expires_at = None
    db.commit()

    # Revoke all existing refresh tokens as a security measure
    revoke_all_refresh_tokens(db, client.id)

    logger.info(f"[Auth] Password reset for client {client.email}")
    return client


# ── Core client operations ───────────────────────────────────────────────────

def register_client(
    db: Session,
    email: str,
    password: str,
    company_name: str,
    full_name: str = "",
) -> Client:
    """Register a new client. Raises ValueError if email already exists."""
    existing = db.query(Client).filter(Client.email == email.lower().strip()).first()
    if existing:
        raise ValueError("An account with this email already exists.")

    client = Client(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        company_name=company_name.strip(),
        full_name=full_name.strip(),
        is_email_verified=False,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    logger.info(f"[Auth] New client registered: {client.email} (id={client.id})")
    return client


def authenticate_client(db: Session, email: str, password: str) -> Optional[Client]:
    """Return the client if credentials are valid and account is active, else None."""
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


def get_client_by_email(db: Session, email: str) -> Optional[Client]:
    return db.query(Client).filter(Client.email == email.lower().strip()).first()
