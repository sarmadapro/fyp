"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel


# --- Document Models ---

class DocumentStatus(BaseModel):
    """Response model for document status."""
    has_document: bool
    document_name: str | None = None
    document_type: str | None = None
    chunk_count: int = 0


class DocumentUploadResponse(BaseModel):
    """Response after successful document upload."""
    message: str
    document_name: str
    chunk_count: int


class DocumentDeleteResponse(BaseModel):
    """Response after document deletion."""
    message: str


# --- Chat Models ---

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str
    sources: list[str] = []
    conversation_id: str


# --- Voice Models ---

class TranscriptionResponse(BaseModel):
    """Response from STT service."""
    text: str
    language: str = ""
    duration: float = 0.0


class SynthesisRequest(BaseModel):
    """Request for TTS service."""
    text: str
    voice: str = "af_sky"


# --- Health ---

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
