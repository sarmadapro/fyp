"""
STT Microservice — Faster-Whisper Speech-to-Text.

Runs as a standalone FastAPI service on port 8001.
Accepts audio files and returns transcriptions.
"""

import io
import os
import time
import logging
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="STT Service",
    description="Speech-to-Text service powered by Faster-Whisper",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model Configuration ──────────────────────────────────────────────
MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "large-v3")
DEVICE = os.getenv("STT_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")

# Global model reference (lazy loaded)
_model = None


def get_model():
    """Lazy-load the Whisper model on first request."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        logger.info(f"Loading Faster-Whisper model: {MODEL_SIZE} (device={DEVICE}, compute={COMPUTE_TYPE})")
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        logger.info("Faster-Whisper model loaded successfully.")
    return _model


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "stt", "model": MODEL_SIZE}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """
    Transcribe an uploaded audio file.

    Accepts: WAV, WebM, MP3, OGG, FLAC, M4A
    Returns: {"text": str, "language": str, "duration": float}
    """
    allowed_types = {
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/webm", "audio/mpeg", "audio/mp3",
        "audio/ogg", "audio/flac", "audio/mp4",
        "audio/x-m4a", "video/webm",
        "application/octet-stream",  # fallback for unknown types
    }

    # Read audio bytes
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    # Save to temp file (faster-whisper needs a file path)
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        model = get_model()
        start_time = time.time()

        segments, info = model.transcribe(
            tmp_path,
            beam_size=5,
            language=None,  # auto-detect
            vad_filter=True,  # voice activity detection
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        # Collect all segments
        full_text = " ".join(segment.text.strip() for segment in segments)
        duration = time.time() - start_time

        logger.info(
            f"Transcribed {file.filename} in {duration:.2f}s | "
            f"Language: {info.language} ({info.language_probability:.2f}) | "
            f"Text: {full_text[:100]}..."
        )

        return {
            "text": full_text,
            "language": info.language,
            "duration": round(duration, 2),
        }

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("STT_PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
