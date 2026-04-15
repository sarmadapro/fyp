"""
Voice service - Real-time conversational pipeline.
"""

import re
import asyncio
import logging
import base64
import time
import traceback
import io
import wave

import httpx
from fastapi import WebSocket

from app.core.config import settings
from app.services.chat_service import chat, chat_stream

logger = logging.getLogger(__name__)

# Timeout for microservice calls (STT/TTS can be slow on first load)
_TIMEOUT = httpx.Timeout(timeout=120.0, connect=10.0)
_STT_TURN_TIMEOUT_SEC = 180.0
_RAG_TURN_TIMEOUT_SEC = 90.0
_TTS_CHUNK_TIMEOUT_SEC = 60.0
_PARTIAL_STT_INTERVAL_SEC = 0.35
_PARTIAL_STT_MIN_AUDIO_SEC = 0.35
_PARTIAL_STT_WINDOW_SEC = 3.0
_PARTIAL_STT_MAX_TEXT_CHARS = 240

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
        resp = await client.get(f"{settings.STT_SERVICE_URL}/health", timeout=10.0)
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"STT health check failed: {e}")
        return False


async def check_tts_health() -> bool:
    """Check if the TTS microservice is reachable."""
    try:
        client = _get_http_client()
        resp = await client.get(f"{settings.TTS_SERVICE_URL}/health", timeout=10.0)
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


# ---------------------------------------------------------------------------
#  Sentence Helpers
# ---------------------------------------------------------------------------

def split_into_sentences(text: str) -> list[str]:
    """Split full text into sentence groups (used by legacy REST path)."""
    raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    raw_sentences = [s.strip() for s in raw_sentences if s.strip()]

    if not raw_sentences:
        return [text] if text.strip() else []

    groups: list[str] = []
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


def extract_complete_sentences(text: str) -> tuple[list[str], str]:
    """Extract complete sentences from a streaming buffer."""
    sentences: list[str] = []
    remaining = text

    while True:
        match = re.search(r"[.!?](?:\s+|$)", remaining)
        if not match:
            break
        sentence = remaining[:match.end()].strip()
        remaining = remaining[match.end():].lstrip()
        if sentence:
            sentences.append(sentence)

    return sentences, remaining


async def iterate_stream_with_timeout(async_gen, timeout_sec: float):
    """Iterate an async generator with per-item timeout."""
    while True:
        try:
            item = await asyncio.wait_for(async_gen.__anext__(), timeout=timeout_sec)
        except StopAsyncIteration:
            break
        yield item


def _new_streaming_session_state() -> dict:
    """Per-websocket temporary state for incremental STT."""
    return {
        "pcm": bytearray(),
        "sample_rate": 16000,
        "last_partial_at": 0.0,
        "last_partial_text": "",
    }


def _wav_to_pcm16(wav_bytes: bytes) -> tuple[bytes, int]:
    """Extract mono PCM16 bytes + sample rate from WAV bytes."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}. Expected 16-bit PCM.")

    if channels == 1:
        return raw, sample_rate

    # Downmix multi-channel PCM16 to mono by taking first channel sample.
    mono = bytearray()
    frame_size = channels * 2
    for i in range(0, len(raw), frame_size):
        mono.extend(raw[i:i + 2])
    return bytes(mono), sample_rate


def _pcm16_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Wrap mono PCM16 bytes in a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def _tail_pcm_window(pcm_bytes: bytes, sample_rate: int, window_sec: float) -> bytes:
    """Return latest window of PCM bytes."""
    max_samples = int(sample_rate * window_sec)
    max_bytes = max_samples * 2
    if len(pcm_bytes) <= max_bytes:
        return pcm_bytes
    return pcm_bytes[-max_bytes:]


async def _emit_partial_transcription_if_ready(websocket: WebSocket, session_state: dict):
    """Run lightweight partial STT on the current buffered utterance."""
    pcm_bytes = bytes(session_state["pcm"])
    sample_rate = int(session_state["sample_rate"])

    # Need enough audio to avoid noisy partial hypotheses.
    min_bytes = int(sample_rate * _PARTIAL_STT_MIN_AUDIO_SEC) * 2
    if len(pcm_bytes) < min_bytes:
        return

    now = time.time()
    if now - float(session_state["last_partial_at"]) < _PARTIAL_STT_INTERVAL_SEC:
        return

    session_state["last_partial_at"] = now
    partial_pcm = _tail_pcm_window(pcm_bytes, sample_rate, _PARTIAL_STT_WINDOW_SEC)
    partial_audio = _pcm16_to_wav_bytes(partial_pcm, sample_rate)

    try:
        result = await transcribe_audio(partial_audio, "partial.wav")
        partial_text = (result.get("text") or "").strip()
        if not partial_text:
            return

        # Avoid spamming duplicate partials to the client.
        prev_text = str(session_state["last_partial_text"])
        if partial_text == prev_text:
            return

        session_state["last_partial_text"] = partial_text
        clipped = partial_text[:_PARTIAL_STT_MAX_TEXT_CHARS]
        await websocket.send_json({
            "type": "partial_transcription",
            "text": clipped,
        })
    except Exception as e:
        logger.debug(f"Partial STT skipped due to error: {e}")


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

    loop = asyncio.get_event_loop()
    chat_result = await loop.run_in_executor(None, chat, user_text, conversation_id)
    answer = chat_result["answer"]
    conversation_id = chat_result["conversation_id"]

    logger.info(f"Voice pipeline: Answer -> '{answer[:100]}...'")

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
    """Main conversational voice loop over WebSocket."""
    conversation_id = None
    streaming_state = _new_streaming_session_state()

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
            "message": "TTS service unavailable - responses will be text-only."
        })

    logger.info(f"Voice session started (STT={'OK' if stt_ok else 'X'}, TTS={'OK' if tts_ok else 'X'})")
    await websocket.send_json({"type": "listening"})

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type", "")

            if msg_type == "config":
                conversation_id = message.get("conversation_id")
                logger.info(f"Voice session configured: conv_id={conversation_id}")

            elif msg_type == "audio_chunk":
                audio_data = message.get("data", "")
                if not audio_data:
                    continue

                try:
                    chunk_bytes = base64.b64decode(audio_data)
                    if not chunk_bytes:
                        continue
                    chunk_pcm, chunk_sample_rate = _wav_to_pcm16(chunk_bytes)
                    if not chunk_pcm:
                        continue
                    streaming_state["sample_rate"] = chunk_sample_rate
                    streaming_state["pcm"].extend(chunk_pcm)

                    await _emit_partial_transcription_if_ready(websocket, streaming_state)
                except Exception as e:
                    logger.debug(f"Ignoring invalid audio_chunk: {e}")

            elif msg_type == "audio_commit":
                buffered_pcm = bytes(streaming_state["pcm"])
                sample_rate = int(streaming_state["sample_rate"])
                streaming_state = _new_streaming_session_state()

                if len(buffered_pcm) < 1000:
                    logger.info(f"Committed audio too short ({len(buffered_pcm)} bytes), skipping.")
                    await websocket.send_json({"type": "listening"})
                    continue

                buffered_audio = _pcm16_to_wav_bytes(buffered_pcm, sample_rate)
                logger.info(
                    f"--- New voice turn (streamed): {len(buffered_pcm)} PCM bytes @ {sample_rate}Hz ---"
                )

                try:
                    conversation_id = await _process_voice_turn(
                        websocket,
                        buffered_audio,
                        conversation_id,
                        filename="recording.wav",
                    )
                except Exception as e:
                    logger.error(f"Voice pipeline error: {e}\n{traceback.format_exc()}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Something went wrong processing your speech. Try again."
                    })

                await websocket.send_json({"type": "listening"})

            elif msg_type == "audio_discard":
                streaming_state = _new_streaming_session_state()
                logger.debug("Discarded current streamed utterance buffer.")

            elif msg_type == "audio_complete":
                # Legacy one-shot utterance; clear any streamed buffer first.
                streaming_state = _new_streaming_session_state()
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

                logger.info(f"--- New voice turn: {len(combined_audio)} bytes of audio ---")

                try:
                    conversation_id = await _process_voice_turn(websocket, combined_audio, conversation_id)
                except Exception as e:
                    logger.error(f"Voice pipeline error: {e}\n{traceback.format_exc()}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Something went wrong processing your speech. Try again."
                    })

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
    filename: str = "recording.wav",
) -> str | None:
    """
    Process a single voice turn:
    1. STT - transcribe the audio
    2. RAG stream - generate text incrementally
    3. TTS - synthesize completed sentences immediately
    """
    turn_start = time.time()

    # 1) STT
    await websocket.send_json({"type": "status", "message": "Transcribing..."})
    stt_start = time.time()

    try:
        transcription = await asyncio.wait_for(
            transcribe_audio(audio_bytes, filename),
            timeout=_STT_TURN_TIMEOUT_SEC,
        )
        user_text = transcription.get("text", "").strip()
    except asyncio.TimeoutError:
        logger.error("STT timed out while processing audio")
        await websocket.send_json({
            "type": "error",
            "message": "Speech transcription timed out. Please try a shorter utterance."
        })
        return conversation_id
    except httpx.ConnectError:
        logger.error("STT service connection refused - is it running on port 8001?")
        await websocket.send_json({
            "type": "error",
            "message": "Can't reach speech-to-text service. Is it running?"
        })
        return conversation_id
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 503:
            logger.warning("STT model still initializing")
            await websocket.send_json({
                "type": "error",
                "message": "Speech model is still loading. Please wait a bit and try again."
            })
        else:
            logger.error(f"STT failed with HTTP status {status}: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Speech transcription failed. Try speaking more clearly."
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
    logger.info(f"[Turn] STT: {stt_time:.2f}s -> '{user_text}'")

    if not user_text:
        await websocket.send_json({
            "type": "error",
            "message": "Couldn't catch that - try speaking more clearly."
        })
        return conversation_id

    await websocket.send_json({"type": "transcription", "text": user_text})

    # 2) RAG stream + 3) Early TTS
    await websocket.send_json({"type": "status", "message": "Thinking..."})
    rag_start = time.time()
    tts_start = time.time()

    tts_available = await check_tts_health()
    if tts_available:
        await websocket.send_json({"type": "status", "message": "Speaking..."})
    else:
        logger.warning("[Turn] TTS unavailable; continuing in text-only mode")

    new_conv_id = conversation_id
    answer = ""
    buffer = ""
    successful_chunks = 0
    chunk_index = 0

    try:
        stream = chat_stream(user_text, conversation_id)
        async for event in iterate_stream_with_timeout(stream, _RAG_TURN_TIMEOUT_SEC):
            event_type = event.get("type")

            if event_type == "token":
                token = event.get("content", "")
                if not token:
                    continue

                answer += token
                buffer += token

                ready_sentences, buffer = extract_complete_sentences(buffer)
                for sentence in ready_sentences:
                    await websocket.send_json({
                        "type": "answer",
                        "text": answer,
                        "conversation_id": new_conv_id,
                    })

                    if not tts_available:
                        continue

                    try:
                        audio_bytes_out = await asyncio.wait_for(
                            synthesize_speech(sentence),
                            timeout=_TTS_CHUNK_TIMEOUT_SEC,
                        )
                        if audio_bytes_out and len(audio_bytes_out) > 44:
                            chunk_index += 1
                            b64_audio = base64.b64encode(audio_bytes_out).decode("utf-8")
                            await websocket.send_json({
                                "type": "audio_chunk",
                                "data": b64_audio,
                                "index": chunk_index,
                                "total": chunk_index,
                            })
                            successful_chunks += 1
                            logger.info(f"[Turn] Early TTS chunk {chunk_index}: {len(audio_bytes_out)} bytes sent")
                    except asyncio.TimeoutError:
                        logger.error(f"[Turn] TTS timed out at early chunk {chunk_index + 1}")
                    except Exception as e:
                        logger.error(f"[Turn] Early TTS failed: {e}")

            elif event_type == "done":
                new_conv_id = event.get("conversation_id", new_conv_id)
            elif event_type == "error":
                raise RuntimeError(event.get("message", "RAG streaming failed"))

        # Flush trailing text as final chunk if needed.
        tail = buffer.strip()
        if tail and tts_available:
            try:
                audio_bytes_out = await asyncio.wait_for(
                    synthesize_speech(tail),
                    timeout=_TTS_CHUNK_TIMEOUT_SEC,
                )
                if audio_bytes_out and len(audio_bytes_out) > 44:
                    chunk_index += 1
                    b64_audio = base64.b64encode(audio_bytes_out).decode("utf-8")
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "data": b64_audio,
                        "index": chunk_index,
                        "total": chunk_index,
                    })
                    successful_chunks += 1
                    logger.info(f"[Turn] Final TTS chunk {chunk_index}: {len(audio_bytes_out)} bytes sent")
            except Exception as e:
                logger.error(f"[Turn] Final TTS chunk failed: {e}")

    except asyncio.TimeoutError:
        logger.error("RAG stream timed out")
        await websocket.send_json({
            "type": "error",
            "message": "I took too long to generate a response. Please try again."
        })
        return conversation_id
    except Exception as e:
        logger.error(f"RAG streaming failed: {e}\n{traceback.format_exc()}")
        await websocket.send_json({
            "type": "error",
            "message": "Sorry, I had trouble generating a response. Try again?"
        })
        return conversation_id

    rag_time = time.time() - rag_start
    logger.info(f"[Turn] RAG stream: {rag_time:.2f}s -> '{answer[:80]}...'")

    await websocket.send_json({
        "type": "answer",
        "text": answer,
        "conversation_id": new_conv_id,
    })

    tts_time = time.time() - tts_start
    total_time = time.time() - turn_start
    logger.info(
        f"[Turn] Early TTS: {tts_time:.2f}s ({successful_chunks} chunks) | "
        f"Total turn: {total_time:.2f}s"
    )

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
    """Legacy streaming voice-to-voice pipeline over WebSocket."""
    await _process_voice_turn(websocket, audio_bytes, conversation_id)
    await websocket.send_json({"type": "done"})
