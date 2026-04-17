"""
Auth API routes.

Endpoints:
  POST /auth/register              — Create account (sends verification email)
  POST /auth/login                 — Login → access + refresh tokens
  POST /auth/refresh               — Rotate refresh token → new access token
  POST /auth/logout                — Revoke all refresh tokens
  GET  /auth/me                    — Current user profile
  POST /auth/verify-email          — Verify email with token
  POST /auth/resend-verification   — Resend verification email
  POST /auth/forgot-password       — Request password reset email
  POST /auth/reset-password        — Reset password with token
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth_service import (
    register_client,
    authenticate_client,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_client_by_id,
    get_client_by_email,
    validate_and_rotate_refresh_token,
    revoke_all_refresh_tokens,
    set_email_verification_token,
    verify_email_token,
    set_password_reset_token,
    reset_password_with_token,
)
from app.models.database import Client, APIKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

_REFRESH_COOKIE = "voicerag_refresh"


# ─── Request / Response Models ────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    company_name: str
    full_name: str = ""

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ResendVerificationRequest(BaseModel):
    email: str


# ─── Auth Dependency ──────────────────────────────────────────────────

def get_current_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Client:
    """FastAPI dependency: validate JWT, return active Client."""
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


# ─── Helper: build auth response ─────────────────────────────────────

def _auth_response(client: Client, access_token: str) -> dict:
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "client": {
            "id":                 client.id,
            "email":              client.email,
            "company_name":       client.company_name,
            "full_name":          client.full_name or "",
            "is_email_verified":  client.is_email_verified,
        },
    }


def _set_refresh_cookie(response: Response, raw_token: str, days: int = 7) -> None:
    """Set HTTP-only cookie with refresh token."""
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=raw_token,
        httponly=True,
        secure=False,    # set True in production (HTTPS)
        samesite="lax",
        max_age=days * 86400,
        path="/auth",
    )


# ─── Endpoints ────────────────────────────────────────────────────────

@router.post("/register")
async def register_endpoint(
    req: RegisterRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Register a new client account.
    Sends an email verification link.
    Returns access token immediately (account works before verification in demo mode).
    """
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

    # Auto-generate a default API key
    full_key, key_prefix, key_hash = APIKey.generate_key()
    api_key = APIKey(client_id=client.id, name="Default Key", key_prefix=key_prefix, key_hash=key_hash)
    db.add(api_key)
    db.commit()

    # Send verification email in the background (failure never blocks registration)
    verification_token = set_email_verification_token(db, client)
    from app.services.email_service import send_verification_email
    background_tasks.add_task(send_verification_email, client.email, client.full_name, verification_token)

    # Issue tokens
    access_token = create_access_token(data={"sub": client.id})
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else ""
    raw_refresh = create_refresh_token(db, client.id, ua, ip)
    _set_refresh_cookie(response, raw_refresh)

    resp = _auth_response(client, access_token)
    resp["api_key"] = full_key  # shown only at registration
    return resp


@router.post("/login")
def login_endpoint(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Login with email and password. Returns access token + sets refresh cookie."""
    client = authenticate_client(db, req.email, req.password)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(data={"sub": client.id})
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else ""
    raw_refresh = create_refresh_token(db, client.id, ua, ip)
    _set_refresh_cookie(response, raw_refresh)

    return _auth_response(client, access_token)


@router.post("/refresh")
def refresh_endpoint(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Rotate refresh token and return a new access token.
    Reads refresh token from HTTP-only cookie or request body.
    """
    # Try cookie first, then body
    raw_refresh = request.cookies.get(_REFRESH_COOKIE)

    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else ""
    client, new_refresh = validate_and_rotate_refresh_token(db, raw_refresh, ua, ip)

    if not client:
        # Clear the bad cookie
        response.delete_cookie(_REFRESH_COOKIE, path="/auth")
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

    access_token = create_access_token(data={"sub": client.id})
    _set_refresh_cookie(response, new_refresh)
    return _auth_response(client, access_token)


@router.post("/logout")
def logout_endpoint(
    response: Response,
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Revoke all refresh tokens and clear the cookie."""
    revoke_all_refresh_tokens(db, current_client.id)
    response.delete_cookie(_REFRESH_COOKIE, path="/auth")
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_profile(
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Get the current client's profile."""
    from app.services.document_service import ClientDocumentService

    doc_service = ClientDocumentService.get_or_create(current_client.id)
    key_count = (
        db.query(APIKey)
        .filter(APIKey.client_id == current_client.id, APIKey.is_active == True)
        .count()
    )

    return {
        "id":                current_client.id,
        "email":             current_client.email,
        "company_name":      current_client.company_name,
        "full_name":         current_client.full_name or "",
        "is_email_verified": current_client.is_email_verified,
        "created_at":        current_client.created_at.isoformat(),
        "has_documents":     doc_service.has_document,
        "api_key_count":     key_count,
    }


@router.post("/verify-email")
def verify_email_endpoint(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Mark email as verified using the token from the verification link."""
    client = verify_email_token(db, req.token)
    if not client:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token. Please request a new one.",
        )
    return {"message": "Email verified successfully. You can now use all features."}


@router.post("/resend-verification")
async def resend_verification_endpoint(
    req: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Resend the email verification link."""
    client = get_client_by_email(db, req.email)

    # Always return success to avoid leaking which emails are registered
    if client and not client.is_email_verified:
        token = set_email_verification_token(db, client)
        from app.services.email_service import send_verification_email
        background_tasks.add_task(send_verification_email, client.email, client.full_name, token)

    return {"message": "If this email is registered and unverified, a new link has been sent."}


@router.post("/forgot-password")
async def forgot_password_endpoint(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Request a password reset email."""
    client = get_client_by_email(db, req.email)

    # Always return success (don't reveal if email exists)
    if client and client.is_active:
        token = set_password_reset_token(db, client)
        from app.services.email_service import send_password_reset_email
        background_tasks.add_task(send_password_reset_email, client.email, client.full_name, token)

    return {"message": "If this email is registered, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password_endpoint(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using the token from the reset email."""
    client = reset_password_with_token(db, req.token, req.new_password)
    if not client:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token. Please request a new link.",
        )
    return {"message": "Password reset successfully. Please log in with your new password."}
