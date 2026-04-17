"""
Widget API — Public chat endpoint authenticated via API key.
This is what the embeddable chat widget calls.
Each API key is linked to a specific client's vector DB.
"""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.database import APIKey, Client
from app.services.document_service import ClientDocumentService
from app.services.chat_service import chat as rag_chat
from app.services.analytics_service import start_trace, finish_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["Widget"])


class WidgetChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class WidgetChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[str] = []


def _validate_api_key(api_key: str) -> str:
    """Validate an API key and return client_id. Raises HTTPException if invalid."""
    if not api_key or not api_key.startswith("vrag_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    key_hash = APIKey.hash_key(api_key)

    db = SessionLocal()
    try:
        db_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        ).first()

        if not db_key:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")

        db_key.last_used_at = datetime.now(timezone.utc)
        db_key.usage_count = (db_key.usage_count or 0) + 1
        client_id = db_key.client_id
        db.commit()
        return client_id
    finally:
        db.close()


@router.post("/chat", response_model=WidgetChatResponse)
def widget_chat(
    req: WidgetChatRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """
    Public chat endpoint for the embeddable widget.
    Authenticated via X-API-Key header, routes to the client's specific FAISS index.
    Delegates entirely to the shared RAG pipeline so persona rules are always enforced.
    """
    client_id = _validate_api_key(x_api_key)
    session_id = req.session_id or str(uuid.uuid4())

    doc_service = ClientDocumentService.get_or_create(client_id)

    result = rag_chat(
        question=req.message,
        conversation_id=session_id,
        doc_service=doc_service,
    )

    return WidgetChatResponse(
        answer=result["answer"],
        session_id=result["conversation_id"],
        sources=result.get("sources", []),
    )


@router.get("/config")
def widget_config(x_api_key: str = Header(..., alias="X-API-Key")):
    """Get widget configuration for a given API key."""
    client_id = _validate_api_key(x_api_key)

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        doc_service = ClientDocumentService.get_or_create(client_id)

        return {
            "company_name": client.company_name,
            "has_documents": doc_service.has_document,
            "document_name": doc_service.document_name,
        }
    finally:
        db.close()
