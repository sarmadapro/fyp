"""
Admin API — platform management for super-admins.

All routes require a valid admin JWT (is_admin=True on the Client row).
Admin tokens are issued by POST /admin/login and carry type="admin_access".

Endpoints:
  POST /admin/login                          — Admin login
  GET  /admin/stats                          — Platform overview stats
  GET  /admin/users                          — Paginated user list (search/filter)
  POST /admin/users                          — Create user from admin panel
  GET  /admin/users/{id}                     — Full user profile + stats
  PATCH /admin/users/{id}/status             — Activate / deactivate
  PATCH /admin/users/{id}/verify             — Force email verified
  PATCH /admin/users/{id}/make-admin         — Toggle admin flag
  DELETE /admin/users/{id}                   — Delete user + all their data
  POST /admin/users/{id}/revoke-sessions     — Revoke all refresh tokens
  GET  /admin/users/{id}/api-keys            — User's API keys
  DELETE /admin/users/{id}/api-keys/{key_id} — Revoke a specific key
  GET  /admin/api-keys                       — All API keys platform-wide
  GET  /admin/analytics                      — Platform-wide usage analytics
"""

import logging
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.database import Client, APIKey, RefreshToken
from app.services.auth_service import (
    hash_password,
    verify_password,
    get_client_by_email,
    revoke_all_refresh_tokens,
)
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
_bearer = HTTPBearer()

ADMIN_TOKEN_TYPE = "admin_access"
ADMIN_TOKEN_EXPIRE_HOURS = 12


# ─── Token helpers ─────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _create_admin_token(client_id: str) -> str:
    payload = {
        "sub":  client_id,
        "type": ADMIN_TOKEN_TYPE,
        "exp":  _utcnow() + timedelta(hours=ADMIN_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_admin_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != ADMIN_TOKEN_TYPE:
            return None
        return payload
    except JWTError:
        return None


# ─── Admin auth dependency ─────────────────────────────────────────────────

def get_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Client:
    """Validate admin JWT. Raises 403 if not admin."""
    token = credentials.credentials
    payload = _decode_admin_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired admin token")

    client = db.query(Client).filter(Client.id == payload.get("sub")).first()
    if not client or not client.is_active or not client.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return client


# ─── Schemas ──────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(BaseModel):
    email: str
    password: str
    company_name: str
    full_name: str = ""
    is_admin: bool = False

    @field_validator("password")
    @classmethod
    def pw_min(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UpdateStatusRequest(BaseModel):
    is_active: bool


# ─── Helpers ──────────────────────────────────────────────────────────────

def _client_dir(client_id: str) -> Path:
    base = Path(settings.DATA_DIR) if hasattr(settings, "DATA_DIR") else Path("data")
    return base / "clients" / client_id


def _user_stats(db: Session, client: Client) -> dict:
    """Compute per-user aggregate stats."""
    keys = db.query(APIKey).filter(APIKey.client_id == client.id).all()
    active_keys  = sum(1 for k in keys if k.is_active)
    total_calls  = sum(k.usage_count for k in keys)
    last_used    = max((k.last_used_at for k in keys if k.last_used_at), default=None)

    # Document status
    idx_dir = _client_dir(client.id) / "indices"
    has_doc = (idx_dir / "doc_meta.txt").exists()
    doc_name = ""
    if has_doc:
        try:
            doc_name = (idx_dir / "doc_meta.txt").read_text().splitlines()[0].strip()
        except Exception:
            pass

    return {
        "id":                client.id,
        "email":             client.email,
        "company_name":      client.company_name,
        "full_name":         client.full_name or "",
        "is_active":         client.is_active,
        "is_email_verified": client.is_email_verified,
        "is_admin":          client.is_admin,
        "created_at":        client.created_at.isoformat() if client.created_at else None,
        "last_seen_at":      client.last_seen_at.isoformat() if client.last_seen_at else None,
        "api_key_count":     len(keys),
        "active_key_count":  active_keys,
        "total_api_calls":   total_calls,
        "last_api_call_at":  last_used.isoformat() if last_used else None,
        "has_document":      has_doc,
        "document_name":     doc_name,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────

@router.post("/login")
def admin_login(req: AdminLoginRequest, db: Session = Depends(get_db)):
    """Authenticate as admin. Returns a short-lived admin JWT."""
    client = get_client_by_email(db, req.email)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, client.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not client.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    if not client.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    token = _create_admin_token(client.id)
    logger.info(f"[Admin] Login: {client.email}")
    return {
        "access_token": token,
        "token_type":   "bearer",
        "expires_in":   ADMIN_TOKEN_EXPIRE_HOURS * 3600,
        "admin": {
            "id":           client.id,
            "email":        client.email,
            "company_name": client.company_name,
            "full_name":    client.full_name or "",
        },
    }


@router.get("/stats")
def platform_stats(
    _admin: Client = Depends(get_admin),
    db: Session = Depends(get_db),
):
    """Platform overview metrics."""
    now = _utcnow()
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users    = db.query(func.count(Client.id)).scalar()
    active_users   = db.query(func.count(Client.id)).filter(Client.is_active == True).scalar()
    verified_users = db.query(func.count(Client.id)).filter(Client.is_email_verified == True).scalar()
    admin_users    = db.query(func.count(Client.id)).filter(Client.is_admin == True).scalar()
    new_7d         = db.query(func.count(Client.id)).filter(Client.created_at >= week_ago).scalar()
    new_30d        = db.query(func.count(Client.id)).filter(Client.created_at >= month_ago).scalar()

    total_keys  = db.query(func.count(APIKey.id)).scalar()
    active_keys = db.query(func.count(APIKey.id)).filter(APIKey.is_active == True).scalar()
    total_calls = db.query(func.coalesce(func.sum(APIKey.usage_count), 0)).scalar()

    # Count clients that have a document indexed
    from pathlib import Path as P
    data_dir = P("data/clients")
    docs_count = 0
    if data_dir.exists():
        for cdir in data_dir.iterdir():
            if (cdir / "indices" / "doc_meta.txt").exists():
                docs_count += 1

    # Top 5 users by API usage
    top_users_raw = (
        db.query(Client.id, Client.email, Client.company_name,
                 func.coalesce(func.sum(APIKey.usage_count), 0).label("calls"))
        .outerjoin(APIKey, APIKey.client_id == Client.id)
        .group_by(Client.id)
        .order_by(desc("calls"))
        .limit(5)
        .all()
    )
    top_users = [
        {"id": r.id, "email": r.email, "company_name": r.company_name, "calls": r.calls}
        for r in top_users_raw
    ]

    # Recent registrations (last 10)
    recent_raw = (
        db.query(Client)
        .order_by(desc(Client.created_at))
        .limit(10)
        .all()
    )
    recent_users = [
        {
            "id":           c.id,
            "email":        c.email,
            "company_name": c.company_name,
            "created_at":   c.created_at.isoformat() if c.created_at else None,
            "is_active":    c.is_active,
            "is_email_verified": c.is_email_verified,
        }
        for c in recent_raw
    ]

    return {
        "users": {
            "total":    total_users,
            "active":   active_users,
            "inactive": total_users - active_users,
            "verified": verified_users,
            "unverified": total_users - verified_users,
            "admins":   admin_users,
            "new_7d":   new_7d,
            "new_30d":  new_30d,
            "with_documents": docs_count,
        },
        "api_keys": {
            "total":  total_keys,
            "active": active_keys,
            "revoked": total_keys - active_keys,
        },
        "usage": {
            "total_api_calls": int(total_calls),
        },
        "top_users":    top_users,
        "recent_users": recent_users,
    }


@router.get("/users")
def list_users(
    search:   str   = Query("", description="Filter by email or company name"),
    status_filter: str = Query("all", description="all | active | inactive | unverified"),
    page:     int   = Query(1, ge=1),
    page_size: int  = Query(20, ge=1, le=100),
    sort_by:  str   = Query("created_at", description="created_at | email | calls"),
    _admin: Client  = Depends(get_admin),
    db: Session     = Depends(get_db),
):
    """List all users with pagination, search, and filtering."""
    q = db.query(Client)

    if search:
        like = f"%{search.lower()}%"
        q = q.filter(
            (func.lower(Client.email).like(like)) |
            (func.lower(Client.company_name).like(like)) |
            (func.lower(Client.full_name).like(like))
        )

    if status_filter == "active":
        q = q.filter(Client.is_active == True)
    elif status_filter == "inactive":
        q = q.filter(Client.is_active == False)
    elif status_filter == "unverified":
        q = q.filter(Client.is_email_verified == False)

    total = q.count()

    if sort_by == "email":
        q = q.order_by(Client.email)
    else:
        q = q.order_by(desc(Client.created_at))

    clients = q.offset((page - 1) * page_size).limit(page_size).all()

    users = []
    for c in clients:
        keys = db.query(APIKey).filter(APIKey.client_id == c.id).all()
        total_calls = sum(k.usage_count for k in keys)
        active_keys = sum(1 for k in keys if k.is_active)
        users.append({
            "id":                c.id,
            "email":             c.email,
            "company_name":      c.company_name,
            "full_name":         c.full_name or "",
            "is_active":         c.is_active,
            "is_email_verified": c.is_email_verified,
            "is_admin":          c.is_admin,
            "created_at":        c.created_at.isoformat() if c.created_at else None,
            "last_seen_at":      c.last_seen_at.isoformat() if c.last_seen_at else None,
            "api_key_count":     len(keys),
            "active_key_count":  active_keys,
            "total_api_calls":   total_calls,
        })

    return {"users": users, "total": total, "page": page, "page_size": page_size}


@router.post("/users", status_code=201)
def create_user(
    req: CreateUserRequest,
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Create a new user account from the admin panel."""
    existing = get_client_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    client = Client(
        email=req.email.lower().strip(),
        hashed_password=hash_password(req.password),
        company_name=req.company_name.strip(),
        full_name=req.full_name.strip(),
        is_active=True,
        is_email_verified=True,  # admin-created accounts skip email verification
        is_admin=req.is_admin,
    )
    db.add(client)
    db.flush()

    full_key, prefix, key_hash = APIKey.generate_key()
    db.add(APIKey(client_id=client.id, name="Default Key", key_prefix=prefix, key_hash=key_hash))
    db.commit()

    logger.info(f"[Admin] Created user: {client.email} (admin={req.is_admin})")
    return {"id": client.id, "email": client.email, "api_key": full_key}


@router.get("/users/{client_id}")
def get_user(
    client_id: str,
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Full profile + stats for one user."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")

    stats = _user_stats(db, client)

    # Active sessions
    active_sessions = (
        db.query(func.count(RefreshToken.id))
        .filter(RefreshToken.client_id == client_id, RefreshToken.revoked == False,
                RefreshToken.expires_at > _utcnow())
        .scalar()
    )
    stats["active_sessions"] = active_sessions

    # API keys detail
    keys = db.query(APIKey).filter(APIKey.client_id == client_id).order_by(desc(APIKey.created_at)).all()
    stats["api_keys"] = [
        {
            "id":          k.id,
            "name":        k.name,
            "key_prefix":  k.key_prefix,
            "is_active":   k.is_active,
            "created_at":  k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "usage_count": k.usage_count,
        }
        for k in keys
    ]

    return stats


@router.patch("/users/{client_id}/status")
def update_user_status(
    client_id: str,
    req: UpdateStatusRequest,
    admin: Client  = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Activate or deactivate a user account."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
    if client.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    client.is_active = req.is_active
    if not req.is_active:
        revoke_all_refresh_tokens(db, client.id)
    db.commit()

    action = "activated" if req.is_active else "deactivated"
    logger.info(f"[Admin] User {client.email} {action} by {admin.email}")
    return {"message": f"User {action} successfully", "is_active": client.is_active}


@router.patch("/users/{client_id}/verify")
def force_verify_email(
    client_id: str,
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Force-mark a user's email as verified."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")

    client.is_email_verified = True
    client.email_verification_token = None
    client.email_verification_expires_at = None
    db.commit()
    return {"message": "Email marked as verified"}


@router.patch("/users/{client_id}/make-admin")
def toggle_admin(
    client_id: str,
    admin: Client  = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Toggle admin status for a user."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
    if client.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own admin status")

    client.is_admin = not client.is_admin
    db.commit()
    action = "granted" if client.is_admin else "revoked"
    logger.info(f"[Admin] Admin privilege {action} for {client.email} by {admin.email}")
    return {"message": f"Admin privilege {action}", "is_admin": client.is_admin}


@router.delete("/users/{client_id}")
def delete_user(
    client_id: str,
    admin: Client  = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Permanently delete a user and all their data."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")
    if client.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    email = client.email

    # Wipe all on-disk data
    client_dir = _client_dir(client_id)
    if client_dir.exists():
        shutil.rmtree(client_dir, ignore_errors=True)

    # Invalidate in-memory service cache
    try:
        from app.services.document_service import ClientDocumentService
        ClientDocumentService._instances.pop(client_id, None)
    except Exception:
        pass

    # Cascade delete via ORM (api_keys + refresh_tokens deleted by cascade)
    db.delete(client)
    db.commit()

    logger.info(f"[Admin] Deleted user {email} by {admin.email}")
    return {"message": f"User '{email}' permanently deleted"}


@router.post("/users/{client_id}/revoke-sessions")
def revoke_user_sessions(
    client_id: str,
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Revoke all active sessions (refresh tokens) for a user."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")

    count = revoke_all_refresh_tokens(db, client_id)
    return {"message": f"Revoked {count} active sessions"}


@router.get("/users/{client_id}/api-keys")
def list_user_api_keys(
    client_id: str,
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """List all API keys for a specific user."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")

    keys = db.query(APIKey).filter(APIKey.client_id == client_id).order_by(desc(APIKey.created_at)).all()
    return [
        {
            "id":          k.id,
            "name":        k.name,
            "key_prefix":  k.key_prefix,
            "is_active":   k.is_active,
            "created_at":  k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "usage_count": k.usage_count,
        }
        for k in keys
    ]


@router.delete("/users/{client_id}/api-keys/{key_id}")
def revoke_user_api_key(
    client_id: str,
    key_id:    str,
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """Revoke a specific API key for any user."""
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.client_id == client_id,
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    if not key.is_active:
        raise HTTPException(status_code=400, detail="Key already revoked")

    key.is_active = False
    db.commit()
    logger.info(f"[Admin] Revoked key {key.key_prefix}... for client {client_id}")
    return {"message": "API key revoked"}


@router.get("/api-keys")
def list_all_api_keys(
    search:    str = Query("", description="Filter by client email or key prefix"),
    active_only: bool = Query(False),
    page:      int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """List all API keys across all clients."""
    q = (
        db.query(APIKey, Client.email, Client.company_name)
        .join(Client, Client.id == APIKey.client_id)
    )

    if search:
        like = f"%{search.lower()}%"
        q = q.filter(
            func.lower(Client.email).like(like) |
            func.lower(APIKey.key_prefix).like(like) |
            func.lower(APIKey.name).like(like)
        )
    if active_only:
        q = q.filter(APIKey.is_active == True)

    total = q.count()
    rows  = q.order_by(desc(APIKey.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    keys = [
        {
            "id":           k.id,
            "client_id":    k.client_id,
            "client_email": email,
            "company_name": company,
            "name":         k.name,
            "key_prefix":   k.key_prefix,
            "is_active":    k.is_active,
            "usage_count":  k.usage_count,
            "created_at":   k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k, email, company in rows
    ]

    return {"keys": keys, "total": total, "page": page, "page_size": page_size}


@router.get("/analytics")
def platform_analytics(
    _admin: Client = Depends(get_admin),
    db: Session    = Depends(get_db),
):
    """
    Platform-wide analytics aggregated from the clients table and API key usage.
    Returns cohort data, top performers, and activity distribution.
    """
    now = _utcnow()

    # User growth by month (last 6 months)
    growth = []
    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        if i > 0:
            month_end = (now.replace(day=1) - timedelta(days=(i - 1) * 30)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            month_end = now
        count = db.query(func.count(Client.id)).filter(
            Client.created_at >= month_start,
            Client.created_at < month_end,
        ).scalar()
        growth.append({
            "month": month_start.strftime("%b %Y"),
            "new_users": count,
        })

    # Top 10 clients by API calls
    top_clients = (
        db.query(Client.id, Client.email, Client.company_name,
                 func.coalesce(func.sum(APIKey.usage_count), 0).label("calls"),
                 func.count(APIKey.id).label("key_count"))
        .outerjoin(APIKey, APIKey.client_id == Client.id)
        .group_by(Client.id)
        .order_by(desc("calls"))
        .limit(10)
        .all()
    )

    # API key activity distribution
    unused = db.query(func.count(APIKey.id)).filter(APIKey.usage_count == 0).scalar()
    low    = db.query(func.count(APIKey.id)).filter(APIKey.usage_count.between(1, 100)).scalar()
    mid    = db.query(func.count(APIKey.id)).filter(APIKey.usage_count.between(101, 1000)).scalar()
    high   = db.query(func.count(APIKey.id)).filter(APIKey.usage_count > 1000).scalar()

    return {
        "user_growth": growth,
        "top_clients": [
            {
                "id":           r.id,
                "email":        r.email,
                "company_name": r.company_name,
                "total_calls":  r.calls,
                "key_count":    r.key_count,
            }
            for r in top_clients
        ],
        "key_activity_distribution": {
            "unused":       unused,
            "low_1_100":    low,
            "mid_101_1000": mid,
            "high_1000+":   high,
        },
    }
