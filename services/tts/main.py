"""
TTS Microservice — Kokoro Text-to-Speech.

Runs as a standalone FastAPI service on port 8002.
Accepts text and returns synthesized audio.
"""

import io
import os
import time
import logging

import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TTS Service",
    description="Text-to-Speech service powered by Kokoro",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configuration ────────────────────────────────────────────────────
TTS_VOICE = os.getenv("TTS_VOICE", "af_sky")
TTS_LANG_CODE = os.getenv("TTS_LANG_CODE", "a")  # 'a' = American English

# Global pipeline reference (lazy loaded)
_pipeline = None


def get_pipeline():
    """Lazy-load the Kokoro TTS pipeline on first request."""
    global _pipeline
    if _pipeline is None:
        from kokoro import KPipeline

        logger.info(f"Loading Kokoro TTS pipeline (lang={TTS_LANG_CODE})...")
        _pipeline = KPipeline(lang_code=TTS_LANG_CODE)
        logger.info("Kokoro TTS pipeline loaded successfully.")
    return _pipeline


# ── Request Models ───────────────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    text: str
    voice: str = TTS_VOICE


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "tts", "voice": TTS_VOICE}


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthesize text to speech.

    Returns: WAV audio bytes.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    if len(request.text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long. Maximum 5000 characters.")

    try:
        pipeline = get_pipeline()
        start_time = time.time()

        # Generate audio using Kokoro
        # The pipeline returns a generator of (graphemes, phonemes, audio) tuples
        audio_chunks = []
        sample_rate = 24000  # Kokoro default sample rate

        for _, _, audio in pipeline(request.text, voice=request.voice):
            if audio is not None:
                audio_chunks.append(audio)

        if not audio_chunks:
            raise HTTPException(status_code=500, detail="No audio generated.")

        # Concatenate all audio chunks
        import numpy as np
        full_audio = np.concatenate(audio_chunks)

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, full_audio, sample_rate, format="WAV", subtype="PCM_16")
        wav_bytes = wav_buffer.getvalue()

        duration = time.time() - start_time
        audio_duration = len(full_audio) / sample_rate

        logger.info(
            f"Synthesized {len(request.text)} chars in {duration:.2f}s | "
            f"Audio duration: {audio_duration:.1f}s | "
            f"Voice: {request.voice}"
        )

        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "X-Audio-Duration": str(round(audio_duration, 2)),
                "X-Processing-Time": str(round(duration, 2)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


@app.post("/synthesize/stream")
async def synthesize_stream(request: SynthesizeRequest):
    """
    Synthesize text to speech with streaming response.
    Returns audio chunks as they are generated for lower latency.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        from fastapi.responses import StreamingResponse

        pipeline = get_pipeline()
        sample_rate = 24000

        async def audio_generator():
            for _, _, audio in pipeline(request.text, voice=request.voice):
                if audio is not None:
                    chunk_buffer = io.BytesIO()
                    sf.write(chunk_buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
                    yield chunk_buffer.getvalue()

        return StreamingResponse(
            audio_generator(),
            media_type="audio/wav",
        )

    except Exception as e:
        logger.error(f"Streaming synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"Streaming synthesis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("TTS_PORT", "8002"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
