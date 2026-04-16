"""
Voice-to-Voice RAG AI Agent — Main FastAPI Application.

SaaS Backend: Multi-tenant document RAG with authentication,
API key management, embeddable widget, and analytics.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db

# Routers — MVP
from app.api.documents import router as document_router
from app.api.chat import router as chat_router
from app.api.voice import router as voice_router
from app.api.analytics import router as analytics_router

# Routers — SaaS
from app.api.auth import router as auth_router
from app.api.api_keys import router as api_keys_router
from app.api.widget import router as widget_router
from app.api.portal import router as portal_router
from app.api.widget_embed import router as widget_embed_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VoiceRAG SaaS Platform",
    description="Multi-tenant voice-to-voice AI assistant powered by RAG.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ──────────────────────────────────────────────

# MVP (single-user, backward-compat)
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "voicerag-saas-backend",
        "version": "2.0.0",
    }


@app.on_event("startup")
async def startup_event():
    # Initialize database tables
    init_db()
    logger.info("[DB] Database initialized (tables created if needed)")

    logger.info("=" * 60)
    logger.info("VoiceRAG SaaS Platform — Backend Starting")
    logger.info(f"  CORS Origins: {settings.CORS_ORIGINS}")
    logger.info(f"  STT Service:  {settings.STT_SERVICE_URL}")
    logger.info(f"  TTS Service:  {settings.TTS_SERVICE_URL}")
    logger.info(f"  LLM Model:    {settings.LLM_MODEL}")
    logger.info(f"  Embedding:    {settings.EMBEDDING_MODEL}")
    
    # Validate critical configuration
    if not settings.GROQ_API_KEY:
        logger.error("=" * 60)
        logger.error("CRITICAL ERROR: GROQ_API_KEY is not set!")
        logger.error("Please add your Groq API key to the .env file")
        logger.error("Get one free at: https://console.groq.com")
        logger.error("=" * 60)
        raise ValueError("GROQ_API_KEY is required but not set in environment")
    else:
        logger.info(f"  Groq API Key: {settings.GROQ_API_KEY[:20]}... (loaded)")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )
