"""
Voice service — Real-time conversational pipeline.

Architecture:
  1. Frontend streams audio chunks over WebSocket as user speaks
  2. Backend accumulates chunks, detects silence (3s gap), triggers STT
  3. Full transcription goes through RAG pipeline
  4. AI response is split into sentences, each sent to TTS separately
  5. TTS audio chunks stream back to frontend for immediate playback

This gives a natural conversational feel — the user just talks,
and the AI responds with voice once they pause.
"""

import re
import logging
import base64
import time

import httpx
from fastapi import WebSocket

from app.core.config import settings
from app.services.chat_service import chat

logger = logging.getLogger(__name__)

# Timeout for microservice calls (STT/TTS can be slow on first load)
_TIMEOUT = httpx.Timeout(timeout=120.0, connect=10.0)


# ---------------------------------------------------------------------------
#  STT / TTS Microservice Calls
# ---------------------------------------------------------------------------

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

    # 2. RAG Chat
    chat_result = chat(user_text, conversation_id)
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
      {"type": "audio_chunk", "data": "<base64 audio>"}   — streaming mic audio
      {"type": "silence_detected"}                        — user stopped speaking (3s silence)
      {"type": "end_session"}                             — user wants to stop
      {"type": "config", "conversation_id": "..."}        — set conversation context

    Protocol (backend -> frontend):
      {"type": "listening"}                               — ready for audio
      {"type": "status", "message": "..."}                — status updates
      {"type": "transcription", "text": "..."}            — what user said
      {"type": "answer", "text": "..."}                   — AI text response
      {"type": "audio_chunk", "data": "<base64>", "index": n, "total": n}
                                                          — TTS audio chunk
      {"type": "speaking_done"}                           — AI finished speaking
      {"type": "error", "message": "..."}                 — errors
    """
    conversation_id = None
    audio_chunks: list[bytes] = []
    is_accumulating = False

    # Signal that we're ready
    await websocket.send_json({"type": "listening"})

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type", "")

            if msg_type == "config":
                conversation_id = message.get("conversation_id")
                logger.info(f"Voice session configured: conv_id={conversation_id}")

            elif msg_type == "audio_chunk":
                # Accumulate audio data from the microphone
                audio_data = message.get("data", "")
                if audio_data:
                    try:
                        decoded = base64.b64decode(audio_data)
                        audio_chunks.append(decoded)
                        is_accumulating = True
                    except Exception as e:
                        logger.warning(f"Failed to decode audio chunk: {e}")

            elif msg_type == "silence_detected":
                # User stopped speaking — process the accumulated audio
                if not audio_chunks or not is_accumulating:
                    await websocket.send_json({"type": "listening"})
                    continue

                is_accumulating = False
                logger.info(f"Silence detected. Processing {len(audio_chunks)} audio chunks...")

                # Combine all audio chunks into a single blob
                combined_audio = b"".join(audio_chunks)
                audio_chunks.clear()

                if len(combined_audio) < 1000:
                    # Too little audio, probably noise
                    logger.info("Audio too short, skipping.")
                    await websocket.send_json({"type": "listening"})
                    continue

                # --- Run the pipeline ---
                try:
                    await _process_voice_turn(
                        websocket, combined_audio, conversation_id
                    )
                except Exception as e:
                    logger.error(f"Voice pipeline error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Something went wrong. Try speaking again."
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
):
    """
    Process a single voice turn:
    1. STT — transcribe the audio
    2. RAG — get AI response
    3. TTS — synthesize response sentence by sentence, streaming audio back
    """
    # ── 1. STT ──
    await websocket.send_json({"type": "status", "message": "Transcribing..."})
    start = time.time()

    transcription = await transcribe_audio(audio_bytes, "recording.webm")
    user_text = transcription.get("text", "").strip()

    stt_time = time.time() - start
    logger.info(f"STT completed in {stt_time:.2f}s: '{user_text}'")

    if not user_text:
        await websocket.send_json({
            "type": "error",
            "message": "Couldn't catch that. Try again?"
        })
        return

    await websocket.send_json({
        "type": "transcription",
        "text": user_text,
    })

    # ── 2. RAG Chat ──
    await websocket.send_json({"type": "status", "message": "Thinking..."})
    start = time.time()

    chat_result = chat(user_text, conversation_id)
    answer = chat_result["answer"]
    new_conv_id = chat_result["conversation_id"]

    rag_time = time.time() - start
    logger.info(f"RAG completed in {rag_time:.2f}s: '{answer[:80]}...'")

    await websocket.send_json({
        "type": "answer",
        "text": answer,
        "conversation_id": new_conv_id,
    })

    # ── 3. TTS — sentence-by-sentence streaming ──
    await websocket.send_json({"type": "status", "message": "Speaking..."})
    start = time.time()

    sentences = split_into_sentences(answer)
    total_sentences = len(sentences)

    if total_sentences == 0:
        await websocket.send_json({"type": "speaking_done"})
        return

    logger.info(f"TTS: splitting response into {total_sentences} sentence group(s)")

    for idx, sentence in enumerate(sentences):
        try:
            audio_bytes_out = await synthesize_speech(sentence)
            if audio_bytes_out:
                b64_audio = base64.b64encode(audio_bytes_out).decode("utf-8")
                await websocket.send_json({
                    "type": "audio_chunk",
                    "data": b64_audio,
                    "index": idx + 1,
                    "total": total_sentences,
                })
        except Exception as e:
            logger.error(f"TTS failed for sentence {idx + 1}: {e}")
            # Continue with remaining sentences even if one fails

    tts_time = time.time() - start
    logger.info(f"TTS completed in {tts_time:.2f}s ({total_sentences} chunks)")

    await websocket.send_json({"type": "speaking_done"})


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
