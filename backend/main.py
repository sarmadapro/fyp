"""
VoiceRAG SaaS Platform — FastAPI Backend.

Multi-tenant voice-to-voice RAG with authentication, API key management,
embeddable widget, and analytics.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.database import init_db


class WidgetCORSMiddleware(BaseHTTPMiddleware):
    """
    Allows cross-origin requests to /widget/* and /widget.js from any origin.
    Must be added AFTER CORSMiddleware so it executes FIRST (outermost wrapper).
    """
    _HEADERS = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
        "Access-Control-Max-Age": "86400",
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_widget = path == "/widget.js" or path.startswith("/widget/") or path.startswith("/vad/")
        if not is_widget:
            return await call_next(request)
        if request.method == "OPTIONS":
            return Response(status_code=200, headers=self._HEADERS)
        response = await call_next(request)
        for k, v in self._HEADERS.items():
            response.headers[k] = v
        return response

# Routers — MVP (single-user, backward-compat)
from app.api.documents import router as document_router
from app.api.chat     import router as chat_router
from app.api.voice    import router as voice_router
from app.api.analytics import router as analytics_router

# Routers — SaaS
from app.api.auth        import router as auth_router
from app.api.api_keys    import router as api_keys_router
from app.api.widget      import router as widget_router
from app.api.portal      import router as portal_router
from app.api.widget_embed import router as widget_embed_router
from app.api.admin       import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        import migrate_admin
        migrate_admin.run()
    except Exception as e:
        logger.warning(f"Admin migration skipped: {e}")
    _seed_admin()
    _check_storage_mount()
    logger.info("=" * 60)
    logger.info("VoiceRAG SaaS Platform v3.0 — Starting")
    logger.info(f"  LLM Provider: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")
    logger.info(f"  STT Service:  {settings.STT_SERVICE_URL}")
    logger.info(f"  TTS Service:  {settings.TTS_SERVICE_URL}")
    logger.info(f"  Embedding:    {settings.EMBEDDING_MODEL}")
    logger.info(f"  CORS Origins: {settings.CORS_ORIGINS}")
    logger.info("=" * 60)
    yield


app = FastAPI(
    title="VoiceRAG SaaS Platform",
    description="Multi-tenant voice-to-voice AI assistant powered by RAG.",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Widget CORS must be added AFTER CORSMiddleware so it wraps it (runs first)
app.add_middleware(WidgetCORSMiddleware)

# ─── Routers ──────────────────────────────────────────────────────────

# MVP
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(analytics_router)

# SaaS
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(widget_router)
app.include_router(portal_router)
app.include_router(widget_embed_router)
app.include_router(admin_router)

# Serve VAD assets (Silero models, ONNX WASM, worklet) for the embedded widget.
# Widget JS on third-party sites loads these from this backend instead of the
# frontend's /public directory (which is inaccessible cross-origin).
_VAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "public")
if os.path.isdir(_VAD_DIR):
    app.mount("/vad", StaticFiles(directory=_VAD_DIR), name="vad-assets")


# ─── Health ───────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "voicerag-saas-backend",
        "version": "3.0.0",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model":    settings.LLM_MODEL,
    }


# ─── Startup ──────────────────────────────────────────────────────────

def _seed_admin():
    """Ensure the default admin account exists."""
    from app.core.database import SessionLocal
    from app.models.database import Client, APIKey
    from app.services.auth_service import hash_password, get_client_by_email

    ADMIN_EMAIL    = "sarmadapro@gmail.com"
    ADMIN_PASSWORD = "11111111"

    db = SessionLocal()
    try:
        client = get_client_by_email(db, ADMIN_EMAIL)
        if not client:
            client = Client(
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                company_name="VoiceRAG Admin",
                full_name="Sarmad",
                is_active=True,
                is_email_verified=True,
                is_admin=True,
            )
            db.add(client)
            db.flush()
            full_key, prefix, key_hash = APIKey.generate_key()
            db.add(APIKey(client_id=client.id, name="Admin Key", key_prefix=prefix, key_hash=key_hash))
            db.commit()
            logger.info(f"[Seed] Admin account created: {ADMIN_EMAIL}")
        elif not client.is_admin:
            client.is_admin = True
            client.is_email_verified = True
            db.commit()
            logger.info(f"[Seed] Admin flag granted to existing account: {ADMIN_EMAIL}")
        else:
            logger.info(f"[Seed] Admin account already exists: {ADMIN_EMAIL}")
    finally:
        db.close()


def _check_storage_mount():
    """
    Verify the data directories are writable at startup.
    On Azure with an Azure Files mount this catches misconfigured mounts early
    rather than failing silently on the first document upload.
    """
    dirs_to_check = {
        "CLIENT_DATA_DIR": settings.CLIENT_DATA_DIR,
        "UPLOAD_DIR":      settings.UPLOAD_DIR,
        "INDEX_DIR":       settings.INDEX_DIR,
    }
    all_ok = True
    for name, path in dirs_to_check.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            probe.write_text("ok")
            probe.unlink()
            logger.info(f"  Storage [{name}]: {path} — OK")
        except Exception as e:
            logger.error(f"  Storage [{name}]: {path} — WRITE FAILED: {e}")
            all_ok = False
    if not all_ok:
        logger.error(
            "One or more storage directories are not writable. "
            "On Azure: verify the Azure Files share is mounted at the correct path "
            "and that CLIENT_DATA_DIR / UPLOAD_DIR / INDEX_DIR env vars point to it."
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )
