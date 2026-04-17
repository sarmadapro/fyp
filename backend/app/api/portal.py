"""
Client Portal API — Authenticated single-document management for multi-tenant SaaS.
Each client has one active document at a time. Uploading a new file overwrites the previous.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_client
from app.models.database import Client
from app.services.document_service import ClientDocumentService
from app.services.chat_service import chat as rag_chat, chat_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Client Portal"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


# ─── Schemas ────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


# ─── Document Endpoints ──────────────────────────────────────────────

@router.get("/document/status")
def portal_document_status(current_client: Client = Depends(get_current_client)):
    """Return status of the currently indexed document."""
    doc_service = ClientDocumentService.get_or_create(current_client.id)
    return {
        "has_document":  doc_service.has_document,
        "document_name": doc_service.document_name,
        "document_type": doc_service.document_type,
        "chunk_count":   doc_service.chunk_count,
    }


@router.post("/document/upload")
async def portal_upload_document(
    file: UploadFile = File(...),
    current_client: Client = Depends(get_current_client),
):
    """
    Upload a document for the authenticated client.
    Fully replaces any existing document — only one per client at a time.
    Invalidates the in-memory service cache so the next request loads the new index.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Use PDF, DOCX, or TXT.",
        )

    # Invalidate cache first — ensures we start with a fresh instance
    ClientDocumentService.invalidate(current_client.id)

    # Create a fresh service instance (not from cache, as we just cleared it)
    doc_service = ClientDocumentService(current_client.id)

    # Remove any previously uploaded raw file BEFORE saving the new one
    doc_service._wipe_uploads()

    # Save new file to disk
    file_path = doc_service.upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    try:
        chunk_count = doc_service.process_and_index(file_path, file.filename, ext)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        logger.error(f"[Portal] Upload failed for client {current_client.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    # Store the freshly-built instance in the cache
    ClientDocumentService._instances[current_client.id] = doc_service

    logger.info(
        f"[Portal] Client {current_client.id} uploaded '{file.filename}' "
        f"— {chunk_count} chunks indexed."
    )

    return {
        "message":       "Document uploaded and indexed successfully",
        "document_name": file.filename,
        "chunk_count":   chunk_count,
    }


@router.delete("/document/delete")
def portal_delete_document(current_client: Client = Depends(get_current_client)):
    """Delete the current document for the authenticated client."""
    doc_service = ClientDocumentService.get_or_create(current_client.id)
    if not doc_service.has_document:
        raise HTTPException(status_code=404, detail="No document to delete")

    doc_service.delete_document()  # also clears from cache internally
    return {"message": "Document deleted successfully"}


# ─── Chat (non-streaming) ──────────────────────────────────────────

@router.post("/chat")
def portal_chat(
    body: ChatRequest,
    current_client: Client = Depends(get_current_client),
):
    """
    Chat against the client's active document (non-streaming).
    Uses the shared RAG pipeline with the client's isolated FAISS index.
    """
    doc_service = ClientDocumentService.get_or_create(current_client.id)

    result = rag_chat(
        question=body.question,
        conversation_id=body.conversation_id,
        doc_service=doc_service,
    )
    return result


# ─── Chat (streaming SSE) ──────────────────────────────────────────

@router.post("/chat/stream")
async def portal_chat_stream(
    body: ChatRequest,
    current_client: Client = Depends(get_current_client),
):
    """
    Authenticated streaming chat (Server-Sent Events).
    Always uses the client's own FAISS index — strictly isolated per client.
    """
    doc_service = ClientDocumentService.get_or_create(current_client.id)

    async def event_generator():
        try:
            async for chunk in chat_stream(
                question=body.question,
                conversation_id=body.conversation_id,
                doc_service=doc_service,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Analytics ─────────────────────────────────────────────────────

@router.get("/analytics/summary")
def portal_analytics_summary(current_client: Client = Depends(get_current_client)):
    """Get analytics summary for this client."""
    from app.services.analytics_service import _entries

    client_entries = list(_entries)
    total       = len(client_entries)
    chat_count  = sum(1 for e in client_entries if e.mode in ("chat", "portal_chat"))
    voice_count = sum(1 for e in client_entries if e.mode == "voice")
    error_count = sum(1 for e in client_entries if e.status == "error")

    def _avg(vals):
        return round(sum(vals) / len(vals), 2) if vals else 0

    lats = [e.latency.total_round_trip_ms for e in client_entries if e.latency.total_round_trip_ms]

    return {
        "total_conversations": total,
        "chat_count":          chat_count,
        "voice_count":         voice_count,
        "error_count":         error_count,
        "avg_latency_ms":      _avg(lats),
    }
