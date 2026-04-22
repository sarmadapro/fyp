"""
Widget API — Public endpoints authenticated via embed API key.
Powers the embeddable chat widget on third-party websites.
"""

import uuid
import base64
import logging
from datetime import datetime, timezone

import json as _json

from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form, WebSocket, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.database import APIKey, Client
from app.services.document_service import ClientDocumentService
from app.services.chat_service import chat as rag_chat, chat_stream
from app.services.voice_service import transcribe_audio, synthesize_speech, handle_voice_conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["Widget"])


# ── Models ────────────────────────────────────────────────────────────

class WidgetChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class WidgetChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[str] = []


class WidgetVoiceResponse(BaseModel):
    transcription: str
    answer: str
    audio_base64: str = ""
    session_id: str


# ── Auth helper ───────────────────────────────────────────────────────

def _validate_api_key(api_key: str) -> str:
    """Validate embed API key → return client_id. Raises 401 if invalid."""
    if not api_key or not api_key.startswith("vrag_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    key_hash = APIKey.hash_key(api_key)
    db = SessionLocal()
    try:
        db_key = (
            db.query(APIKey)
            .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)
            .first()
        )
        if not db_key:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")

        db_key.last_used_at = datetime.now(timezone.utc)
        db_key.usage_count = (db_key.usage_count or 0) + 1
        client_id = db_key.client_id
        db.commit()
        return client_id
    finally:
        db.close()


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/config")
def widget_config(x_api_key: str = Header(..., alias="X-API-Key")):
    """Return widget configuration (company name, doc status)."""
    client_id = _validate_api_key(x_api_key)
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        doc_service = ClientDocumentService.get_or_create(client_id)
        return {
            "company_name":  client.company_name,
            "has_documents": doc_service.has_document,
            "document_name": doc_service.document_name,
        }
    finally:
        db.close()


@router.post("/chat", response_model=WidgetChatResponse)
def widget_chat(
    req: WidgetChatRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Text chat via embed key — routed to the client's FAISS index."""
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


@router.post("/chat/stream")
async def widget_chat_stream(
    req: WidgetChatRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Streaming widget chat (SSE). Tokens arrive as they are generated."""
    client_id = _validate_api_key(x_api_key)
    session_id = req.session_id or str(uuid.uuid4())
    doc_service = ClientDocumentService.get_or_create(client_id)

    async def event_generator():
        try:
            async for chunk in chat_stream(
                question=req.message,
                conversation_id=session_id,
                doc_service=doc_service,
            ):
                yield f"data: {_json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/voice", response_model=WidgetVoiceResponse)
async def widget_voice(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """
    Voice pipeline via embed key: audio → STT → RAG → TTS.
    Returns transcription, text answer, and base64 WAV audio.
    """
    client_id = _validate_api_key(x_api_key)
    audio_bytes = await file.read()

    # STT
    try:
        stt = await transcribe_audio(audio_bytes, file.filename or "audio.webm")
        transcription = stt.get("text", "").strip()
        language = stt.get("language", "en")
    except Exception as e:
        logger.error(f"[Widget/Voice] STT failed: {e}")
        raise HTTPException(status_code=503, detail="Speech recognition unavailable. Please try text input.")

    if not transcription:
        raise HTTPException(status_code=400, detail="Could not understand audio. Please speak clearly and try again.")

    # RAG
    session_id = session_id or str(uuid.uuid4())
    doc_service = ClientDocumentService.get_or_create(client_id)
    result = rag_chat(
        question=transcription,
        conversation_id=session_id,
        doc_service=doc_service,
    )
    answer = result["answer"]

    # TTS — best effort, never blocks the response
    audio_b64 = ""
    try:
        tts_bytes = await synthesize_speech(answer, language=language)
        audio_b64 = base64.b64encode(tts_bytes).decode()
    except Exception as e:
        logger.warning(f"[Widget/Voice] TTS skipped: {e}")

    logger.info(f"[Widget/Voice] client={client_id} q='{transcription[:60]}' a='{answer[:60]}'")

    return WidgetVoiceResponse(
        transcription=transcription,
        answer=answer,
        audio_base64=audio_b64,
        session_id=result["conversation_id"],
    )


@router.websocket("/voice/ws")
async def widget_voice_ws(
    websocket: WebSocket,
    api_key: str = Query(...),
    language: str | None = Query(default=None),
):
    """
    Real-time voice pipeline via embed key — identical to the client portal's
    WebSocket voice endpoint but authenticated with the embed API key instead
    of a JWT. Routes audio through the tenant's isolated RAG index.
    """
    await websocket.accept()

    try:
        client_id = _validate_api_key(api_key)
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "message": exc.detail})
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
    finally:
        db.close()

    if not client:
        await websocket.send_json({"type": "error", "message": "Client not found"})
        await websocket.close(code=4404)
        return

    logger.info(f"[Widget/Voice/WS] client={client_id} session opened")
    await handle_voice_conversation(websocket, client=client, language=language or None)
