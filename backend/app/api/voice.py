"""
Voice API routes.
Handles voice-to-voice interaction via STT -> RAG -> TTS pipeline.

Endpoints:
  POST /voice/transcribe     — One-shot STT
  POST /voice/synthesize     — One-shot TTS  
  POST /voice/chat           — One-shot full pipeline (REST)
  WS   /voice/conversation   — Real-time conversational loop (new)
  WS   /voice/stream         — Legacy streaming (backward compat)
"""

import logging
import base64

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Query,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import TranscriptionResponse
from app.services.auth_service import decode_access_token, get_client_by_id
from app.services.voice_service import (
    transcribe_audio,
    synthesize_speech,
    voice_to_voice,
    voice_to_voice_stream,
    handle_voice_conversation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_endpoint(file: UploadFile = File(...)):
    """Transcribe an audio file to text using the STT service."""
    try:
        audio_bytes = await file.read()
        result = await transcribe_audio(audio_bytes, file.filename)
        return TranscriptionResponse(**result)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/synthesize")
async def synthesize_endpoint(text: str, voice: str = "af_sky"):
    """Convert text to speech using the TTS service."""
    try:
        audio_bytes = await synthesize_speech(text, voice)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


@router.post("/chat")
async def voice_chat_endpoint(
    file: UploadFile = File(...),
    conversation_id: str | None = None,
):
    """
    Full voice-to-voice chat (REST, non-streaming):
    Upload audio -> STT -> RAG -> TTS -> return text + audio
    """
    try:
        audio_bytes = await file.read()
        result = await voice_to_voice(audio_bytes, file.filename, conversation_id)

        return {
            "transcription": result["transcription"],
            "answer": result["answer"],
            "audio_base64": base64.b64encode(result["audio"]).decode("utf-8") if result["audio"] else "",
            "conversation_id": result["conversation_id"],
        }
    except Exception as e:
        logger.error(f"Voice chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice chat failed: {str(e)}")


@router.websocket("/conversation")
async def voice_conversation_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Real-time conversational voice WebSocket.

    Requires a valid JWT in the ?token= query param so the server can
    resolve the authenticated client and route RAG against that client's
    isolated FAISS index. Anonymous connections are rejected.
    """
    await websocket.accept()

    client = None
    if token:
        payload = decode_access_token(token)
        if payload:
            client_id = payload.get("sub")
            if client_id:
                resolved = get_client_by_id(db, client_id)
                if resolved and resolved.is_active:
                    client = resolved

    if client is None:
        logger.warning("Voice WS rejected: missing/invalid auth token")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required. Please log in again.",
            })
        finally:
            await websocket.close(code=4401)
        return

    logger.info(f"Voice conversation WebSocket connected (client={client.id})")

    try:
        await handle_voice_conversation(websocket, client=client)
    except WebSocketDisconnect:
        logger.info(f"Voice conversation WebSocket disconnected (client={client.id})")
    except Exception as e:
        logger.error(f"Voice conversation error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/stream")
async def voice_websocket_endpoint(websocket: WebSocket, conversation_id: str | None = None):
    """
    Legacy WebSocket endpoint for voice interaction.
    Accepts a single audio blob, processes it, streams back results.
    """
    await websocket.accept()
    try:
        audio_bytes = await websocket.receive_bytes()
        await voice_to_voice_stream(websocket, audio_bytes, "audio.wav", conversation_id)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "text": str(e)})
        except:
            pass
        finally:
            await websocket.close()
