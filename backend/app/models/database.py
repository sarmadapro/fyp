"""
SQLAlchemy ORM models for multi-tenant SaaS.

Tables:
  - clients:       Registered users/companies
  - api_keys:      Per-client API keys for widget authentication
  - refresh_tokens: JWT refresh tokens for session management
"""

import uuid
import secrets
import hashlib
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _generate_id():
    return str(uuid.uuid4())


class Client(Base):
    """A registered client (company/person) on the platform."""
    __tablename__ = "clients"

    id                    = Column(String(36), primary_key=True, default=_generate_id)
    email                 = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password       = Column(String(255), nullable=False)
    company_name          = Column(String(255), nullable=False)
    full_name             = Column(String(255), default="")
    is_active             = Column(Boolean, default=True)

    # Email verification
    is_email_verified               = Column(Boolean, default=False)
    email_verification_token        = Column(String(64), nullable=True, index=True)
    email_verification_expires_at   = Column(DateTime, nullable=True)

    # Password reset
    password_reset_token            = Column(String(64), nullable=True, index=True)
    password_reset_expires_at       = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    api_keys       = relationship("APIKey",       back_populates="client", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client {self.email}>"


class APIKey(Base):
    """API key for widget authentication. Each client can have multiple keys."""
    __tablename__ = "api_keys"

    id         = Column(String(36), primary_key=True, default=_generate_id)
    client_id  = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    name       = Column(String(255), default="Default Key")
    key_prefix = Column(String(12), nullable=False)  # First chars for display
    key_hash   = Column(String(64), nullable=False, unique=True)  # SHA-256
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    last_used_at = Column(DateTime, nullable=True)
    usage_count  = Column(Integer, default=0)

    client = relationship("Client", back_populates="api_keys")

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """
        Generate a new API key.
        Returns: (full_key, key_prefix, key_hash)
        """
        raw      = secrets.token_hex(24)
        full_key = f"vrag_{raw}"
        prefix   = full_key[:12]
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, prefix, key_hash

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... client={self.client_id}>"


class RefreshToken(Base):
    """Long-lived refresh tokens for session management."""
    __tablename__ = "refresh_tokens"

    id          = Column(String(36), primary_key=True, default=_generate_id)
    client_id   = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash  = Column(String(64), nullable=False, unique=True, index=True)
    expires_at  = Column(DateTime, nullable=False)
    created_at  = Column(DateTime, default=_utcnow)
    revoked     = Column(Boolean, default=False)
    user_agent  = Column(String(512), nullable=True)   # for audit trail
    ip_address  = Column(String(45), nullable=True)    # IPv4/IPv6

    client = relationship("Client", back_populates="refresh_tokens")

    @staticmethod
    def generate() -> tuple[str, str]:
        """Generate a raw refresh token and its hash. Returns (raw, hash)."""
        raw  = secrets.token_urlsafe(48)
        h    = hashlib.sha256(raw.encode()).hexdigest()
        return raw, h

    def __repr__(self):
        return f"<RefreshToken client={self.client_id} expires={self.expires_at}>"
