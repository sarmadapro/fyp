"""
API Key management routes.
Clients can create, list, and revoke API keys for widget authentication.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_client
from app.models.database import Client, APIKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class CreateKeyRequest(BaseModel):
    name: str = "Default Key"


class KeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: str
    last_used_at: str | None
    usage_count: int


class NewKeyResponse(KeyResponse):
    full_key: str  # Only shown once at creation!


@router.post("", response_model=NewKeyResponse)
def create_api_key(
    req: CreateKeyRequest,
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Generate a new API key for the current client."""
    # Limit keys per client
    active_count = db.query(APIKey).filter(
        APIKey.client_id == current_client.id,
        APIKey.is_active == True,
    ).count()

    if active_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 active API keys per account")

    full_key, key_prefix, key_hash = APIKey.generate_key()

    api_key = APIKey(
        client_id=current_client.id,
        name=req.name.strip() or "Default Key",
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"[APIKey] Created key {key_prefix}... for client {current_client.email}")

    return NewKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        full_key=full_key,
        is_active=True,
        created_at=api_key.created_at.isoformat(),
        last_used_at=None,
        usage_count=0,
    )


@router.get("", response_model=list[KeyResponse])
def list_api_keys(
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """List all API keys for the current client."""
    keys = db.query(APIKey).filter(
        APIKey.client_id == current_client.id,
    ).order_by(APIKey.created_at.desc()).all()

    return [
        KeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            created_at=k.created_at.isoformat(),
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            usage_count=k.usage_count,
        )
        for k in keys
    ]


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: str,
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Revoke (deactivate) an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.client_id == current_client.id,
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()

    logger.info(f"[APIKey] Revoked key {api_key.key_prefix}... for client {current_client.email}")
    return {"message": "API key revoked"}
