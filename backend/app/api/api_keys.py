"""
Embed Key management routes.
Each tenant has exactly ONE website embed key used for widget/plugin integration.
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

router = APIRouter(prefix="/api-keys", tags=["Embed Key"])


class KeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: str
    last_used_at: str | None
    usage_count: int


class NewKeyResponse(KeyResponse):
    full_key: str  # Only shown once at creation / regeneration


def _key_response(k: APIKey) -> KeyResponse:
    return KeyResponse(
        id=k.id,
        name=k.name,
        key_prefix=k.key_prefix,
        is_active=k.is_active,
        created_at=k.created_at.isoformat(),
        last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        usage_count=k.usage_count,
    )


@router.get("", response_model=list[KeyResponse])
def get_embed_key(
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Return the tenant's embed key (at most one active)."""
    keys = (
        db.query(APIKey)
        .filter(APIKey.client_id == current_client.id)
        .order_by(APIKey.created_at.desc())
        .all()
    )
    return [_key_response(k) for k in keys]


@router.post("/regenerate", response_model=NewKeyResponse)
def regenerate_embed_key(
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """
    Atomically revoke the existing embed key and generate a new one.
    The full key is returned once — it cannot be retrieved again.
    """
    # Revoke all active keys
    db.query(APIKey).filter(
        APIKey.client_id == current_client.id,
        APIKey.is_active == True,
    ).update({"is_active": False}, synchronize_session=False)
    db.commit()

    full_key, key_prefix, key_hash = APIKey.generate_key()
    api_key = APIKey(
        client_id=current_client.id,
        name="Website Embed Key",
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"[EmbedKey] Regenerated key {key_prefix}... for {current_client.email}")

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


@router.delete("/{key_id}")
def revoke_embed_key(
    key_id: str,
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Revoke the embed key (admin use / emergency)."""
    api_key = (
        db.query(APIKey)
        .filter(APIKey.id == key_id, APIKey.client_id == current_client.id)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=404, detail="Embed key not found")

    api_key.is_active = False
    db.commit()

    logger.info(f"[EmbedKey] Revoked key {api_key.key_prefix}... for {current_client.email}")
    return {"message": "Embed key revoked"}
