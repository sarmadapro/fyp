"""
Voice service — Real-time conversational pipeline.

Architecture:
  1. Frontend VAD detects speech → sends complete utterance as WAV
  2. Backend receives full WAV → STT transcription
  3. Full transcription goes through RAG pipeline  
  4. AI response is split into sentences, each sent to TTS separately
  5. TTS audio chunks stream back to frontend for immediate playback

This gives a natural conversational feel — the user just talks,
and the AI responds with voice once they pause.
"""

import re
import asyncio
import logging
import base64
import time
import traceback

import httpx
from fastapi import WebSocket

from app.core.config import settings
from app.services.chat_service import chat

logger = logging.getLogger(__name__)

# Timeout for microservice calls (STT/TTS can be slow on first load)
_TIMEOUT = httpx.Timeout(timeout=120.0, connect=10.0)

# Shared async HTTP client (connection pooling, much faster than per-request)
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=_TIMEOUT)
    return _http_client


# ---------------------------------------------------------------------------
#  Health Checks
# ---------------------------------------------------------------------------

async def check_stt_health() -> bool:
    """Check if the STT microservice is reachable."""
    try:
        client = _get_http_client()
        resp = await client.get(f"{settings.STT_SERVICE_URL}/health", timeout=5.0)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"STT health check failed: {e}")
        return False


async def check_tts_health() -> bool:
    """Check if the TTS microservice is reachable."""
    try:
        client = _get_http_client()
        resp = await client.get(f"{settings.TTS_SERVICE_URL}/health", timeout=5.0)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"TTS health check failed: {e}")
        return False


# ---------------------------------------------------------------------------
#  STT / TTS Microservice Calls
# ---------------------------------------------------------------------------

async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """
    Send audio to the STT microservice for transcription.
    Returns: {"text": str, "language": str, "duration": float}
    """
    # Determine content type from extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
    content_types = {
        "wav": "audio/wav",
        "webm": "audio/webm",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }
    content_type = content_types.get(ext, "audio/wav")

    logger.info(f"[STT] Sending {len(audio_bytes)} bytes as {filename} ({content_type})")

    client = _get_http_client()
    files = {"file": (filename, audio_bytes, content_type)}
    response = await client.post(
        f"{settings.STT_SERVICE_URL}/transcribe",
        files=files,
    )
    response.raise_for_status()
    result = response.json()
    logger.info(f"[STT] Result: text='{result.get('text', '')[:80]}', lang={result.get('language')}")
    return result


async def synthesize_speech(text: str, voice: str = "af_sky") -> bytes:
    """
    Send text to the TTS microservice for synthesis.
    Returns: audio bytes (WAV format)
    """
    logger.info(f"[TTS] Synthesizing {len(text)} chars: '{text[:60]}...'")

    client = _get_http_client()
    response = await client.post(
        f"{settings.TTS_SERVICE_URL}/synthesize",
        json={"text": text, "voice": voice},
    )
    response.raise_for_status()

    audio_bytes = response.content
    logger.info(f"[TTS] Received {len(audio_bytes)} bytes of audio")
    return audio_bytes


async def synthesize_speech_stream(text: str, voice: str = "af_sky"):
    """
    Send text to the TTS microservice and stream the audio response.
    Yields audio bytes chunks.
    """
    client = _get_http_client()
    async with client.stream(
        "POST",
        f"{settings.TTS_SERVICE_URL}/synthesize/stream",
        json={"text": text, "voice": voice},
    ) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            yield chunk


# ---------------------------------------------------------------------------
#  Sentence Splitting for TTS Streaming
# ---------------------------------------------------------------------------

def split_into_sentences(text: str) -> list[str]:
    """
    Split AI response into natural sentence groups for TTS.
    Groups short sentences together so TTS chunks are balanced
    (not too short, not too long).
    """
    # Split on sentence-ending punctuation
    raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    raw_sentences = [s.strip() for s in raw_sentences if s.strip()]

    if not raw_sentences:
        return [text] if text.strip() else []

    # Group short sentences together (aim for ~50-150 char chunks)
    groups = []
    current_group = ""

    for sentence in raw_sentences:
        if not current_group:
            current_group = sentence
        elif len(current_group) + len(sentence) + 1 < 150:
            current_group += " " + sentence
        else:
            groups.append(current_group)
            current_group = sentence

    if current_group:
        groups.append(current_group)

    return groups


# ---------------------------------------------------------------------------
#  Legacy: Full voice-to-voice (non-streaming, kept for /voice/chat REST)
# ---------------------------------------------------------------------------

async def voice_to_voice(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    conversation_id: str | None = None,
) -> dict:
    """
    Full voice-to-voice pipeline (REST, non-streaming):
    1. Transcribe audio (STT)
    2. Send transcription through RAG chat
    3. Synthesize response (TTS)
    """
    # 1. STT
    logger.info("Voice pipeline: Starting transcription...")
    transcription = await transcribe_audio(audio_bytes, filename)
    user_text = transcription.get("text", "").strip()

    if not user_text:
        return {
            "transcription": "",
            "answer": "I couldn't catch that. Could you try again?",
            "audio": b"",
            "conversation_id": conversation_id or "",
        }

    logger.info(f"Voice pipeline: Transcribed -> '{user_text}'")

    # 2. RAG Chat — run in thread to avoid blocking the async event loop
    loop = asyncio.get_event_loop()
    chat_result = await loop.run_in_executor(None, chat, user_text, conversation_id)
    answer = chat_result["answer"]
    conversation_id = chat_result["conversation_id"]

    logger.info(f"Voice pipeline: Answer -> '{answer[:100]}...'")

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


# ---------------------------------------------------------------------------
#  Real-Time Conversational WebSocket Pipeline
# ---------------------------------------------------------------------------

async def handle_voice_conversation(websocket: WebSocket):
    """
    Main conversational voice loop over WebSocket.

    Protocol (frontend -> backend):
      {"type": "audio_complete", "data": "<base64 WAV>"}   — complete utterance (VAD-captured)
      {"type": "end_session"}                               — user wants to stop
      {"type": "config", "conversation_id": "..."}          — set conversation context

    Protocol (backend -> frontend):
      {"type": "listening"}                               — ready for audio
      {"type": "status", "message": "..."}                — status updates
      {"type": "transcription", "text": "..."}            — what user said
      {"type": "answer", "text": "...", "conversation_id": "..."}  — AI text response
      {"type": "audio_chunk", "data": "<base64>", "index": n, "total": n}
                                                          — TTS audio chunk
      {"type": "speaking_done"}                           — AI finished speaking
      {"type": "error", "message": "..."}                 — errors
    """
    # Persistent conversation_id across the entire WebSocket session
    conversation_id = None

    # Health-check STT and TTS before starting
    stt_ok = await check_stt_health()
    tts_ok = await check_tts_health()

    if not stt_ok:
        logger.error("STT service is NOT reachable! Voice will not work.")
        await websocket.send_json({
            "type": "error",
            "message": "Speech-to-text service is not running. Please start the STT service on port 8001."
        })
        return

    if not tts_ok:
        logger.warning("TTS service is NOT reachable. Voice responses will be text-only.")
        await websocket.send_json({
            "type": "status",
            "message": "TTS service unavailable — responses will be text-only."
        })

    logger.info(f"Voice session started (STT={'✓' if stt_ok else '✗'}, TTS={'✓' if tts_ok else '✗'})")

    # Signal that we're ready
    await websocket.send_json({"type": "listening"})

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type", "")

            if msg_type == "config":
                conversation_id = message.get("conversation_id")
                logger.info(f"Voice session configured: conv_id={conversation_id}")

            elif msg_type == "audio_complete":
                # Complete utterance from VAD — process it directly
                audio_data = message.get("data", "")
                if not audio_data:
                    logger.warning("[Voice] Received empty audio_complete")
                    await websocket.send_json({"type": "listening"})
                    continue

                try:
                    combined_audio = base64.b64decode(audio_data)
                except Exception as e:
                    logger.warning(f"Failed to decode audio_complete: {e}")
                    await websocket.send_json({"type": "listening"})
                    continue

                if len(combined_audio) < 1000:
                    logger.info(f"Audio too short ({len(combined_audio)} bytes), skipping.")
                    await websocket.send_json({"type": "listening"})
                    continue

                logger.info(f"━━━ New voice turn: {len(combined_audio)} bytes of audio ━━━")

                try:
                    # Pass conversation_id and receive the updated one
                    conversation_id = await _process_voice_turn(
                        websocket, combined_audio, conversation_id
                    )
                except Exception as e:
                    logger.error(f"Voice pipeline error: {e}\n{traceback.format_exc()}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Something went wrong processing your speech. Try again."
                    })

                # Ready for next turn
                await websocket.send_json({"type": "listening"})

            elif msg_type == "end_session":
                logger.info("Voice session ended by client.")
                break

    except Exception as e:
        logger.info(f"Voice WebSocket closed: {e}")


async def _process_voice_turn(
    websocket: WebSocket,
    audio_bytes: bytes,
    conversation_id: str | None,
) -> str | None:
    """
    Process a single voice turn:
    1. STT — transcribe the audio
    2. RAG — get AI response
    3. TTS — synthesize response sentence by sentence, streaming audio back

    Returns the conversation_id (may be newly created if None was passed).
    """
    turn_start = time.time()

    # ── 1. STT ──
    await websocket.send_json({"type": "status", "message": "Transcribing..."})
    stt_start = time.time()

    try:
        transcription = await transcribe_audio(audio_bytes, "recording.wav")
        user_text = transcription.get("text", "").strip()
    except httpx.ConnectError:
        logger.error("STT service connection refused — is it running on port 8001?")
        await websocket.send_json({
            "type": "error",
            "message": "Can't reach speech-to-text service. Is it running?"
        })
        return conversation_id
    except Exception as e:
        logger.error(f"STT failed: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Speech transcription failed. Try speaking more clearly."
        })
        return conversation_id

    stt_time = time.time() - stt_start
    logger.info(f"[Turn] STT: {stt_time:.2f}s → '{user_text}'")

    if not user_text:
        await websocket.send_json({
            "type": "error",
            "message": "Couldn't catch that — try speaking more clearly."
        })
        return conversation_id

    await websocket.send_json({
        "type": "transcription",
        "text": user_text,
    })

    # ── 2. RAG Chat ──
    await websocket.send_json({"type": "status", "message": "Thinking..."})
    rag_start = time.time()

    # Run the synchronous chat() in a thread pool to avoid blocking
    # the async event loop. Without this, the WebSocket would hang.
    loop = asyncio.get_event_loop()
    try:
        chat_result = await loop.run_in_executor(None, chat, user_text, conversation_id)
    except Exception as e:
        logger.error(f"RAG chat failed: {e}\n{traceback.format_exc()}")
        await websocket.send_json({
            "type": "error",
            "message": "Sorry, I had trouble generating a response. Try again?"
        })
        return conversation_id

    answer = chat_result["answer"]
    new_conv_id = chat_result["conversation_id"]

    rag_time = time.time() - rag_start
    logger.info(f"[Turn] RAG: {rag_time:.2f}s → '{answer[:80]}...'")

    # Send the text answer immediately (so user sees it even if TTS fails)
    await websocket.send_json({
        "type": "answer",
        "text": answer,
        "conversation_id": new_conv_id,
    })

    # ── 3. TTS — sentence-by-sentence streaming ──
    await websocket.send_json({"type": "status", "message": "Speaking..."})
    tts_start = time.time()

    sentences = split_into_sentences(answer)
    total_sentences = len(sentences)

    if total_sentences == 0:
        logger.warning("[Turn] No sentences to synthesize")
        await websocket.send_json({"type": "speaking_done"})
        total_time = time.time() - turn_start
        logger.info(f"[Turn] Complete in {total_time:.2f}s (no TTS)")
        return new_conv_id

    logger.info(f"[Turn] TTS: {total_sentences} sentence group(s) to synthesize")

    # Re-check TTS health before starting synthesis
    tts_available = await check_tts_health()
    if not tts_available:
        logger.warning("[Turn] TTS service unavailable — skipping audio synthesis")
        await websocket.send_json({"type": "speaking_done"})
        total_time = time.time() - turn_start
        logger.info(f"[Turn] Complete in {total_time:.2f}s (TTS unavailable)")
        return new_conv_id

    successful_chunks = 0
    for idx, sentence in enumerate(sentences):
        try:
            audio_bytes_out = await synthesize_speech(sentence)
            if audio_bytes_out and len(audio_bytes_out) > 44:  # WAV header is 44 bytes
                b64_audio = base64.b64encode(audio_bytes_out).decode("utf-8")
                await websocket.send_json({
                    "type": "audio_chunk",
                    "data": b64_audio,
                    "index": idx + 1,
                    "total": total_sentences,
                })
                successful_chunks += 1
                logger.info(f"[Turn] TTS chunk {idx + 1}/{total_sentences}: {len(audio_bytes_out)} bytes sent")
            else:
                logger.warning(f"[Turn] TTS chunk {idx + 1}/{total_sentences}: empty or too small")
        except httpx.ConnectError:
            logger.error(f"[Turn] TTS connection failed at chunk {idx + 1}")
            break  # Don't try remaining chunks if connection is down
        except Exception as e:
            logger.error(f"[Turn] TTS failed for chunk {idx + 1}: {e}")
            # Continue with remaining sentences even if one fails

    tts_time = time.time() - tts_start
    total_time = time.time() - turn_start
    logger.info(
        f"[Turn] TTS: {tts_time:.2f}s ({successful_chunks}/{total_sentences} chunks) | "
        f"Total turn: {total_time:.2f}s"
    )

    # Always send speaking_done so the frontend can resume VAD
    await websocket.send_json({"type": "speaking_done"})

    return new_conv_id


# ---------------------------------------------------------------------------
#  Legacy streaming (kept for backward compat)
# ---------------------------------------------------------------------------

async def voice_to_voice_stream(
    websocket: WebSocket,
    audio_bytes: bytes,
    filename: str = "audio.wav",
    conversation_id: str | None = None,
):
    """
    Legacy streaming voice-to-voice pipeline over WebSocket.
    Kept for backward compatibility with the old /voice/stream endpoint.
    """
    await _process_voice_turn(websocket, audio_bytes, conversation_id)
    await websocket.send_json({"type": "done"})
