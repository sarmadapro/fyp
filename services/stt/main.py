"""
STT Microservice - OpenAI Whisper API.

Runs as a standalone FastAPI service on port 8001.
Forwards audio to OpenAI's whisper-1 model and returns transcriptions.
"""

import os
import logging
import time
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import AsyncOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set — transcription requests will fail.")

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="STT Service",
    description="Speech-to-Text via OpenAI Whisper API",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "stt",
        "model": "whisper-1",
        "ready": bool(OPENAI_API_KEY),
        "loading": False,
        "error": None if OPENAI_API_KEY else "OPENAI_API_KEY not configured",
        "preprocessing": False,
    }


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str | None = Form(default=None)):
    """
    Transcribe an uploaded audio file via OpenAI Whisper API.

    Accepts: WAV, WebM, MP3, OGG, FLAC, M4A
    Returns: {"text": str, "language": str, "duration": float, "audio_duration_s": float}
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    filename = file.filename or "audio.webm"
    start = time.time()

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    content_types = {
        "wav":  "audio/wav",
        "webm": "audio/webm",
        "mp3":  "audio/mpeg",
        "ogg":  "audio/ogg",
        "flac": "audio/flac",
        "m4a":  "audio/mp4",
    }
    content_type = content_types.get(ext, "audio/webm")

    # Pin to English to skip language detection (meaningfully faster).
    # Pass "auto" explicitly if multilingual support is needed.
    forced_lang = (language or "").strip().lower()
    if not forced_lang or forced_lang == "auto":
        forced_lang = "en"

    try:
        response = await _client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_bytes, content_type),
            response_format="json",
            language=forced_lang,
        )

        text = (response.text or "").strip()
        elapsed = round(time.time() - start, 2)

        logger.info(
            f"[STT] {filename} → {elapsed}s | lang={forced_lang} | text={text[:100]!r}"
        )

        return {
            "text": text,
            "language": forced_lang,
            "duration": elapsed,
            "audio_duration_s": elapsed,
        }

    except Exception as e:
        logger.error(f"[STT] OpenAI Whisper error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("STT_PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
