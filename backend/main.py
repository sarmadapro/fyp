"""
Voice-to-Voice RAG AI Agent — Main FastAPI Application.

This is the central backend server that orchestrates:
- Document upload and RAG indexing
- Text-based chat with the AI assistant
- Voice-to-voice interaction via STT/TTS microservices
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.documents import router as document_router
from app.api.chat import router as chat_router
from app.api.voice import router as voice_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Voice RAG AI Agent",
    description="Voice-to-voice AI assistant powered by RAG over your documents.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(voice_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "voice-rag-backend",
        "version": "1.0.0",
    }


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("Voice RAG AI Agent — Backend Starting")
    logger.info(f"  CORS Origins: {settings.CORS_ORIGINS}")
    logger.info(f"  STT Service:  {settings.STT_SERVICE_URL}")
    logger.info(f"  TTS Service:  {settings.TTS_SERVICE_URL}")
    logger.info(f"  LLM Model:    {settings.LLM_MODEL}")
    logger.info(f"  Embedding:    {settings.EMBEDDING_MODEL}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )
