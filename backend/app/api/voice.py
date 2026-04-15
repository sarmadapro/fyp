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

from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.models.schemas import TranscriptionResponse
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
async def voice_conversation_endpoint(websocket: WebSocket):
    """
    Real-time conversational voice WebSocket.

    The client streams mic audio chunks, the server detects silence,
    transcribes, runs RAG, and streams back TTS audio sentence-by-sentence.

    This is the primary endpoint for the voice page.
    """
    await websocket.accept()
    logger.info("Voice conversation WebSocket connected")

    try:
        await handle_voice_conversation(websocket)
    except WebSocketDisconnect:
        logger.info("Voice conversation WebSocket disconnected")
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
