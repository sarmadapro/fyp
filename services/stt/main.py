"""
STT Microservice - Faster-Whisper Speech-to-Text.

Runs as a standalone FastAPI service on port 8001.
Accepts audio files and returns transcriptions.
"""

import os
import time
import logging
import tempfile
import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load project-level .env so STT_* settings work when service is started standalone.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Add CUDA DLLs to PATH for faster-whisper GPU support
import sys

if sys.platform == "win32":
    venv_path = Path(__file__).resolve().parent / "venv"
    cuda_paths = [
        venv_path / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin",
        venv_path / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin",
        venv_path / "Lib" / "site-packages" / "nvidia" / "cuda_nvrtc" / "bin",
        venv_path / "Lib" / "site-packages" / "nvidia" / "cuda_runtime" / "bin",
    ]
    for cuda_path in cuda_paths:
        if cuda_path.exists():
            os.add_dll_directory(str(cuda_path))
            os.environ["PATH"] = str(cuda_path) + os.pathsep + os.environ.get("PATH", "")
            logger.info(f"Added CUDA DLL directory: {cuda_path}")

# Use HTTP downloads instead of XET backend to reduce download fragility on some setups.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

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

# Model configuration
MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "small")
DEVICE = os.getenv("STT_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")
FALLBACK_MODEL_SIZE = os.getenv("STT_FALLBACK_MODEL_SIZE", "small")

# Global model state
_model = None
_model_lock = threading.Lock()
_model_loading = False
_model_error = None


def get_model():
    """Lazy-load the Whisper model."""
    global _model, _model_loading, _model_error

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        from faster_whisper import WhisperModel

        _model_loading = True
        _model_error = None

        logger.info(
            f"Loading Faster-Whisper model: {MODEL_SIZE} "
            f"(device={DEVICE}, compute={COMPUTE_TYPE})"
        )

        try:
            _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
            logger.info("Faster-Whisper model loaded successfully.")
        except Exception as e:
            logger.exception(f"Primary model load failed: {e}")

            if MODEL_SIZE != FALLBACK_MODEL_SIZE:
                logger.warning(
                    f"Falling back to model '{FALLBACK_MODEL_SIZE}' "
                    f"(device={DEVICE}, compute={COMPUTE_TYPE})"
                )
                _model = WhisperModel(
                    FALLBACK_MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE
                )
                logger.info("Fallback Faster-Whisper model loaded successfully.")
            else:
                _model_error = str(e)
                raise
        finally:
            _model_loading = False

    return _model


@app.on_event("startup")
async def startup_warmup():
    async def _warm():
        try:
            await asyncio.to_thread(get_model)
        except Exception as e:
            logger.error(f"STT warmup failed: {e}")

    asyncio.create_task(_warm())


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "stt",
        "model": MODEL_SIZE,
        "ready": _model is not None,
        "loading": _model_loading,
        "error": _model_error,
    }


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """
    Transcribe an uploaded audio file.

    Accepts: WAV, WebM, MP3, OGG, FLAC, M4A
    Returns: {"text": str, "language": str, "duration": float}
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    suffix = os.path.splitext(file.filename)[1] if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        if _model is None and _model_loading:
            raise HTTPException(
                status_code=503,
                detail="STT model is still initializing. Please retry in a few moments.",
            )

        def run_transcription(path: str):
            model = get_model()
            start_time = time.time()

            segments, info = model.transcribe(
                path,
                beam_size=5,
                language=None,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )

            full_text = " ".join(segment.text.strip() for segment in segments)
            duration = time.time() - start_time
            return full_text, info, duration

        full_text, info, duration = await asyncio.to_thread(run_transcription, tmp_path)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("STT_PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
