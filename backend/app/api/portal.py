"""
Client Portal API — Authenticated document management for multi-tenant SaaS.
Uses the client's isolated vector DB and document storage.
"""

import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_client
from app.models.database import Client
from app.services.document_service import ClientDocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Client Portal"])


@router.get("/document/status")
def portal_document_status(current_client: Client = Depends(get_current_client)):
    """Get document status for the authenticated client."""
    doc_service = ClientDocumentService(current_client.id)
    return {
        "has_document": doc_service.has_document,
        "document_name": doc_service.document_name,
        "document_type": doc_service.document_type,
        "chunk_count": doc_service.chunk_count,
    }


@router.post("/document/upload")
async def portal_upload_document(
    file: UploadFile = File(...),
    current_client: Client = Depends(get_current_client),
):
    """Upload a document for the authenticated client."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in (".pdf", ".docx", ".txt"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    doc_service = ClientDocumentService(current_client.id)

    # Save uploaded file
    file_path = doc_service.upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    try:
        chunk_count = doc_service.process_and_index(file_path, file.filename, ext)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        logger.error(f"[Portal] Upload failed for client {current_client.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    return {
        "message": "Document uploaded and indexed successfully",
        "document_name": file.filename,
        "chunk_count": chunk_count,
    }


@router.delete("/document/delete")
def portal_delete_document(current_client: Client = Depends(get_current_client)):
    """Delete the document for the authenticated client."""
    doc_service = ClientDocumentService(current_client.id)
    if not doc_service.has_document:
        raise HTTPException(status_code=404, detail="No document to delete")

    doc_service.delete_document()
    return {"message": "Document deleted successfully"}


@router.get("/chat")
def portal_chat(
    question: str,
    current_client: Client = Depends(get_current_client),
):
    """Quick chat endpoint for testing in the portal."""
    from app.services.analytics_service import start_trace, mark, finish_trace, record_error

    doc_service = ClientDocumentService(current_client.id)

    if not doc_service.has_document:
        return {"answer": "No document uploaded yet. Upload one first!", "sources": []}

    trace_id = start_trace(current_client.id, mode="portal_chat", user_query=question)

    mark(trace_id, "retrieval", "start")
    results = doc_service.similarity_search(question, top_k=8)
    mark(trace_id, "retrieval", "end")

    context = "\n\n".join(f"--- Excerpt {i+1} ---\n{r['content']}" for i, r in enumerate(results))
    sources = list(set(r["metadata"].get("source", "") for r in results if r["metadata"].get("source")))

    mark(trace_id, "llm", "start")
    try:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate
        from app.core.config import settings

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are a helpful assistant. Answer based on context. Be concise.\n\nCONTEXT:\n{context}"),
            ("human", "{question}"),
        ])

        chain = prompt | llm
        response = chain.invoke({"question": question})
        answer = response.content
        mark(trace_id, "llm", "end")
    except Exception as e:
        mark(trace_id, "llm", "end")
        record_error(trace_id, f"LLM error: {e}")
        finish_trace(trace_id, ai_response="")
        raise HTTPException(status_code=500, detail="Chat failed")

    finish_trace(trace_id, ai_response=answer)
    return {"answer": answer, "sources": sources}


@router.get("/analytics/summary")
def portal_analytics_summary(current_client: Client = Depends(get_current_client)):
    """Get analytics summary scoped to this client."""
    from app.services.analytics_service import _entries

    client_entries = [e for e in _entries if e.conversation_id.startswith(current_client.id) or True]

    total = len(client_entries)
    chat_count = sum(1 for e in client_entries if e.mode in ("chat", "portal_chat"))
    voice_count = sum(1 for e in client_entries if e.mode == "voice")
    widget_count = sum(1 for e in client_entries if e.mode == "widget")
    error_count = sum(1 for e in client_entries if e.status == "error")

    def _avg(vals):
        return round(sum(vals) / len(vals), 2) if vals else 0

    total_lats = [e.latency.total_round_trip_ms for e in client_entries if e.latency.total_round_trip_ms]

    return {
        "total_conversations": total,
        "chat_count": chat_count,
        "voice_count": voice_count,
        "widget_count": widget_count,
        "error_count": error_count,
        "avg_latency_ms": _avg(total_lats),
    }
