"""
Voice API routes.
Handles voice-to-voice interaction via STT → RAG → TTS pipeline.
"""

import logging
import base64

from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.models.schemas import TranscriptionResponse
from app.services.voice_service import transcribe_audio, synthesize_speech, voice_to_voice, voice_to_voice_stream

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
    Full voice-to-voice chat:
    1. Upload audio recording
    2. Transcribes the audio (STT)
    3. Sends through RAG chat pipeline
    4. Synthesizes the answer (TTS)
    5. Returns both text and audio response

    Response: JSON with transcription, answer text, and base64-encoded audio.
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


@router.websocket("/stream")
async def voice_websocket_endpoint(websocket: WebSocket, conversation_id: str | None = None):
    """
    WebSocket endpoint for real-time voice interaction.
    Accepts audio bytes, streams back status, transcription, and TTS audio chunks.
    """
    await websocket.accept()
    try:
        # Receive audio recording as bytes
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
