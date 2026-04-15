"""
Voice service.
Proxies requests to STT and TTS microservices and orchestrates the
voice-to-voice pipeline: audio → STT → RAG chat → TTS → audio.
"""

import io
import logging
import base64

import httpx
from fastapi import WebSocket

from app.core.config import settings
from app.services.chat_service import chat

logger = logging.getLogger(__name__)

# Timeout for microservice calls (STT/TTS can be slow on first load)
_TIMEOUT = httpx.Timeout(timeout=120.0, connect=10.0)


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """
    Send audio to the STT microservice for transcription.
    Returns: {"text": str, "language": str, "duration": float}
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        files = {"file": (filename, audio_bytes, "audio/wav")}
        response = await client.post(
            f"{settings.STT_SERVICE_URL}/transcribe",
            files=files,
        )
        response.raise_for_status()
        return response.json()


async def synthesize_speech(text: str, voice: str = "af_sky") -> bytes:
    """
    Send text to the TTS microservice for synthesis.
    Returns: audio bytes (WAV format)
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            f"{settings.TTS_SERVICE_URL}/synthesize",
            json={"text": text, "voice": voice},
        )
        response.raise_for_status()
        return response.content


async def voice_to_voice(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    conversation_id: str | None = None,
) -> dict:
    """
    Full voice-to-voice pipeline:
    1. Transcribe audio (STT)
    2. Send transcription through RAG chat
    3. Synthesize response (TTS)

    Returns: {
        "transcription": str,
        "answer": str,
        "audio": bytes,
        "conversation_id": str
    }
    """
    # 1. STT
    logger.info("Voice pipeline: Starting transcription...")
    transcription = await transcribe_audio(audio_bytes, filename)
    user_text = transcription.get("text", "").strip()

    if not user_text:
        return {
            "transcription": "",
            "answer": "I couldn't understand what you said. Please try again.",
            "audio": b"",
            "conversation_id": conversation_id or "",
        }

    logger.info(f"Voice pipeline: Transcribed → '{user_text}'")

    # 2. RAG Chat
    chat_result = chat(user_text, conversation_id)
    answer = chat_result["answer"]
    conversation_id = chat_result["conversation_id"]

    logger.info(f"Voice pipeline: Answer → '{answer[:100]}...'")

    # 3. TTS
    logger.info("Voice pipeline: Synthesizing speech...")
    audio = await synthesize_speech(answer)

    logger.info("Voice pipeline: Complete.")
    return {
        "transcription": user_text,
        "answer": answer,
        "audio": audio,
        "conversation_id": conversation_id,
    }


async def synthesize_speech_stream(text: str, voice: str = "af_sky"):
    """
    Send text to the TTS microservice and stream the audio response.
    Yields audio bytes chunks.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        async with client.stream(
            "POST",
            f"{settings.TTS_SERVICE_URL}/synthesize/stream",
            json={"text": text, "voice": voice},
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk


async def voice_to_voice_stream(
    websocket: WebSocket,
    audio_bytes: bytes,
    filename: str = "audio.wav",
    conversation_id: str | None = None,
):
    """
    Streaming voice-to-voice pipeline over WebSocket.
    """
    # 1. STT
    await websocket.send_json({"type": "status", "message": "Transcribing..."})
    transcription = await transcribe_audio(audio_bytes, filename)
    user_text = transcription.get("text", "").strip()

    if not user_text:
        await websocket.send_json({
            "type": "error",
            "text": "I couldn't understand what you said. Please try again."
        })
        return

    await websocket.send_json({
        "type": "transcription",
        "text": user_text
    })

    # 2. RAG Chat
    await websocket.send_json({"type": "status", "message": "Thinking..."})
    chat_result = chat(user_text, conversation_id)
    answer = chat_result["answer"]
    new_conv_id = chat_result["conversation_id"]

    await websocket.send_json({
        "type": "answer",
        "text": answer,
        "conversation_id": new_conv_id
    })

    # 3. TTS Stream
    await websocket.send_json({"type": "status", "message": "Speaking..."})
    try:
        async for audio_chunk in synthesize_speech_stream(answer):
            if audio_chunk:
                base64_chunk = base64.b64encode(audio_chunk).decode("utf-8")
                await websocket.send_json({
                    "type": "audio_chunk",
                    "data": base64_chunk
                })
    except Exception as e:
        logger.error(f"TTS Streaming error: {e}")
    
    await websocket.send_json({"type": "done"})
