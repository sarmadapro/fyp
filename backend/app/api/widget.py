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
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.database import APIKey
from app.services.document_service import ClientDocumentService
from app.services.analytics_service import start_trace, mark, record_error, finish_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["Widget"])


class WidgetChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class WidgetChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[str] = []


def _validate_api_key(api_key: str) -> tuple[str, str]:
    """
    Validate an API key and return (client_id, key_id).
    Raises HTTPException if invalid.
    """
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

        # Update usage stats
        db_key.last_used_at = datetime.now(timezone.utc)
        db_key.usage_count = (db_key.usage_count or 0) + 1
        client_id = db_key.client_id
        key_id = db_key.id
        db.commit()

        return client_id, key_id
    finally:
        db.close()


# In-memory conversation histories per session (widget sessions)
_widget_conversations: dict[str, list[dict]] = {}


@router.post("/chat", response_model=WidgetChatResponse)
def widget_chat(
    req: WidgetChatRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """
    Public chat endpoint for the embeddable widget.
    Authenticated via X-API-Key header, routes to the client's specific vector DB.
    """
    # 1. Validate API key → get client_id
    client_id, key_id = _validate_api_key(x_api_key)

    # 2. Get or create session
    session_id = req.session_id or str(uuid.uuid4())

    # 3. Start analytics trace
    trace_id = start_trace(
        conversation_id=session_id,
        mode="widget",
        user_query=req.message,
    )

    # 4. Load client-specific document service
    doc_service = ClientDocumentService(client_id)

    if not doc_service.has_document:
        finish_trace(trace_id, ai_response="No document uploaded yet.")
        return WidgetChatResponse(
            answer="I don't have any knowledge base set up yet. The admin needs to upload documents first.",
            session_id=session_id,
        )

    # 5. Retrieve from client's FAISS index
    mark(trace_id, "retrieval", "start")
    search_results = doc_service.similarity_search(req.message, top_k=8)
    mark(trace_id, "retrieval", "end")

    if not search_results:
        finish_trace(trace_id, ai_response="No relevant info found.")
        return WidgetChatResponse(
            answer="I couldn't find relevant information in my knowledge base for that question.",
            session_id=session_id,
        )

    # 6. Build context from chunks
    context_parts = []
    for i, r in enumerate(search_results, 1):
        context_parts.append(f"--- Excerpt {i} ---\n{r['content']}")
    context = "\n\n".join(context_parts)

    sources = list(set(
        r["metadata"].get("source", "") for r in search_results if r["metadata"].get("source")
    ))

    # 7. Build conversation history for this session
    history = _widget_conversations.get(session_id, [])

    # 8. Call LLM
    mark(trace_id, "llm", "start")
    try:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.messages import HumanMessage, AIMessage
        from app.core.config import settings

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        system_prompt = f"""You are a helpful assistant. Answer questions based on the provided context.
Be concise, natural, and friendly. Don't mention sources or documents — just answer naturally.

CONTEXT:
{context}"""

        messages = [("system", system_prompt)]
        for h in history[-10:]:
            messages.append(("human", h["user"]))
            messages.append(("assistant", h["ai"]))
        messages.append(("human", req.message))

        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | llm
        response = chain.invoke({})
        answer = response.content

        mark(trace_id, "llm", "end")
    except Exception as e:
        mark(trace_id, "llm", "end")
        record_error(trace_id, f"LLM failed: {e}")
        finish_trace(trace_id, ai_response="")
        logger.error(f"Widget LLM error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")

    # 9. Save to session history
    if session_id not in _widget_conversations:
        _widget_conversations[session_id] = []
    _widget_conversations[session_id].append({"user": req.message, "ai": answer})

    # Keep sessions manageable
    if len(_widget_conversations[session_id]) > 50:
        _widget_conversations[session_id] = _widget_conversations[session_id][-20:]

    # 10. Finalize trace
    finish_trace(trace_id, ai_response=answer)

    return WidgetChatResponse(
        answer=answer,
        session_id=session_id,
        sources=sources,
    )


@router.get("/config")
def widget_config(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Get widget configuration for a given API key.
    Returns the client name and basic settings.
    """
    client_id, _ = _validate_api_key(x_api_key)

    db = SessionLocal()
    try:
        from app.models.database import Client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        doc_service = ClientDocumentService(client_id)

        return {
            "company_name": client.company_name,
            "has_documents": doc_service.has_document,
            "document_name": doc_service.document_name,
        }
    finally:
        db.close()
