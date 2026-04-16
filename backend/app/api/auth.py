"""
Auth API routes — Register, Login, Get Profile.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import (
    register_client,
    authenticate_client,
    create_access_token,
    decode_access_token,
    get_client_by_id,
)
from app.models.database import Client, APIKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


# ─── Request/Response Models ────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    company_name: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client: dict


class ProfileResponse(BaseModel):
    id: str
    email: str
    company_name: str
    full_name: str
    created_at: str
    has_documents: bool = False
    api_key_count: int = 0


# ─── Auth Dependency ────────────────────────────────────────────────

def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Client:
    """FastAPI dependency: extract and validate JWT, return Client."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    client_id = payload.get("sub")
    if not client_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    client = get_client_by_id(db, client_id)
    if not client or not client.is_active:
        raise HTTPException(status_code=401, detail="Account not found or deactivated")

    return client


# ─── Endpoints ──────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
def register_endpoint(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new client account."""
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not req.company_name.strip():
        raise HTTPException(status_code=400, detail="Company name is required")

    try:
        client = register_client(
            db=db,
            email=req.email,
            password=req.password,
            company_name=req.company_name,
            full_name=req.full_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Auto-generate a default API key for the new client
    full_key, key_prefix, key_hash = APIKey.generate_key()
    api_key = APIKey(
        client_id=client.id,
        name="Default Key",
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()

    token = create_access_token(data={"sub": client.id})

    return AuthResponse(
        access_token=token,
        client={
            "id": client.id,
            "email": client.email,
            "company_name": client.company_name,
            "full_name": client.full_name,
            "api_key": full_key,  # Only shown once at registration!
        },
    )


@router.post("/login", response_model=AuthResponse)
def login_endpoint(req: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    client = authenticate_client(db, req.email, req.password)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(data={"sub": client.id})

    return AuthResponse(
        access_token=token,
        client={
            "id": client.id,
            "email": client.email,
            "company_name": client.company_name,
            "full_name": client.full_name,
        },
    )


@router.get("/me", response_model=ProfileResponse)
def get_profile(
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get current client profile."""
    from app.services.document_service import ClientDocumentService

    doc_service = ClientDocumentService(current_client.id)
    key_count = db.query(APIKey).filter(
        APIKey.client_id == current_client.id,
        APIKey.is_active == True,
    ).count()

    return ProfileResponse(
        id=current_client.id,
        email=current_client.email,
        company_name=current_client.company_name,
        full_name=current_client.full_name or "",
        created_at=current_client.created_at.isoformat(),
        has_documents=doc_service.has_document,
        api_key_count=key_count,
    )
