"""
STT Microservice - Faster-Whisper Speech-to-Text.

Runs as a standalone FastAPI service on port 8001.
Accepts audio files and returns transcriptions.

Noise-robustness pipeline (applied in order):
  1. High-pass filter  — removes rumble / low-freq noise below 60 Hz (preserves male voices)
  2. Spectral noise reduction (noisereduce)  — gentle (prop_decrease=0.35) to preserve speech
  3. RMS normalisation  — cautious (+6 dB cap) to avoid amplifying noise
  4. Faster-Whisper with relaxed VAD  — transcribes with threshold=0.45, catches messy speech
  5. Per-segment confidence gate  — uses relaxed thresholds for noisy conditions
  6. Hallucination filter  — removes only obvious noise artifacts and repetition loops
"""

import os
import re
import io
import time
import wave
import logging
import tempfile
import asyncio
import threading
from pathlib import Path

import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load project-level .env
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

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

app = FastAPI(
    title="STT Service",
    description="Speech-to-Text service powered by Faster-Whisper",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "small")
DEVICE = os.getenv("STT_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")
FALLBACK_MODEL_SIZE = os.getenv("STT_FALLBACK_MODEL_SIZE", "small")

_model = None
_model_lock = threading.Lock()
_model_loading = False
_model_error = None

# ── Lazy-loaded preprocessing libs ──────────────────────────────────────────
# We import noisereduce / scipy only when the first transcription request
# arrives so startup is not blocked if those wheels are still installing.
_nr = None
_butter = None
_sosfilt = None


def _ensure_preprocess_libs():
    global _nr, _butter, _sosfilt
    if _nr is None:
        try:
            import noisereduce as _noisereduce
            from scipy.signal import butter, sosfilt
            _nr = _noisereduce
            _butter = butter
            _sosfilt = sosfilt
            logger.info("Audio preprocessing libs (noisereduce, scipy) loaded.")
        except ImportError as e:
            logger.warning(f"Preprocessing libs unavailable ({e}); skipping denoising.")


# ── Hallucination filter ─────────────────────────────────────────────────────

# Phrases Whisper emits on near-silence / pure noise. We only suppress these
# when Whisper's own confidence is also low (see _filter_segment_by_confidence).
# Common single-word responses ("yes", "no", "ok") are NOT blanket-blocked
# because they are legitimate user utterances.
_NOISE_ARTIFACTS = {
    "[music]", "[applause]", "[ music ]", "[ applause ]",
    "subtitles by", "subtitles", "captions", "[background noise]",
    "[noise]", "[silence]", "[inaudible]",
}

# These phrases are ALWAYS hallucinations regardless of confidence.
_ALWAYS_HALLUCINATION = {
    "", ".", "..", "...",
}

_REPETITION_RE = re.compile(r"(.{4,})\1{2,}", re.IGNORECASE)  # 4+ char chunk repeated 3+ times
_BRACKET_ONLY_RE = re.compile(r"^\[.*\]$")
_PUNCT_ONLY_RE = re.compile(r"^[\s\.\,\!\?\-]+$")


def _filter_hallucinations(text: str, avg_no_speech_prob: float, avg_logprob: float) -> str:
    """
    Conservative hallucination filter.

    Only removes obvious noise artifacts and repetition loops.
    Preserves legitimate short answers ("yes", "no", "ok") even if low confidence,
    because these are often correct in noisy conditions.
    """
    cleaned = text.strip()

    if cleaned.lower() in _ALWAYS_HALLUCINATION:
        return ""

    if _BRACKET_ONLY_RE.match(cleaned) or _PUNCT_ONLY_RE.match(cleaned):
        return ""

    if _REPETITION_RE.search(cleaned):
        logger.debug(f"[Filter] Repetition loop detected: {cleaned[:60]!r}")
        return ""

    # Known noise-artifact phrases: only suppress when BOTH indicators are very bad.
    if cleaned.lower() in _NOISE_ARTIFACTS and avg_no_speech_prob > 0.75:
        logger.debug(f"[Filter] Noise artifact dropped: {cleaned!r}")
        return ""

    return cleaned


# ── Audio preprocessing ──────────────────────────────────────────────────────

_TARGET_RMS_DBFS = -18.0   # normalise speech to -18 dBFS
_HP_CUTOFF_HZ = 60.0       # remove rumble below 60 Hz (protects male voices ~85-180 Hz)
_HP_ORDER = 4


def _read_wav_as_float32(path: str):
    """Return (float32 array, sample_rate) from a WAV file."""
    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sample_width, np.int16)
    audio = np.frombuffer(raw, dtype=dtype).astype(np.float32)

    scale = float(2 ** (8 * sample_width - 1))
    audio /= scale

    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    return audio, sample_rate


def _write_float32_as_wav(audio: np.ndarray, sample_rate: int, path: str):
    pcm16 = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm16 * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())


def _preprocess_audio(src_path: str) -> str:
    """
    Three-stage noise-cleaning pipeline:
      1. High-pass filter  — removes low-frequency rumble
      2. Spectral noise reduction (noisereduce) — attenuates stationary noise
      3. RMS normalisation — consistent loudness for Whisper

    Returns path to the cleaned WAV (a new temp file) or src_path on failure.
    """
    _ensure_preprocess_libs()
    if _nr is None:
        return src_path  # libs unavailable, skip

    try:
        audio, sr = _read_wav_as_float32(src_path)

        if len(audio) == 0:
            return src_path

        # 1. High-pass filter
        sos = _butter(_HP_ORDER, _HP_CUTOFF_HZ / (sr / 2.0), btype="highpass", output="sos")
        audio = _sosfilt(sos, audio)

        # 2. Spectral noise reduction
        # stationary=True models a constant noise floor (fan, HVAC, traffic).
        # prop_decrease=0.35 is gentler to avoid removing speech harmonics.
        # Whisper is trained on noisy audio, so aggressive denoising often hurts.
        audio = _nr.reduce_noise(
            y=audio,
            sr=sr,
            stationary=True,
            prop_decrease=0.35,
            n_fft=512,          # smaller FFT → faster for short clips
            n_jobs=1,
        )

        # 3. RMS normalisation (gentler to avoid amplifying noise in quiet clips)
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms > 1e-6:
            target_rms = 10 ** (_TARGET_RMS_DBFS / 20.0)
            gain = target_rms / rms
            # Cap gain at +6 dB to avoid amplifying noise in quiet+noisy audio.
            # Better to preserve SNR than boost quiet noisy signals.
            gain = min(gain, 10 ** (6.0 / 20.0))
            audio = np.clip(audio * gain, -1.0, 1.0)

        out_path = src_path + "_clean.wav"
        _write_float32_as_wav(audio, sr, out_path)
        logger.debug(f"[Preprocess] rms={rms:.4f} → cleaned WAV at {out_path}")
        return out_path

    except Exception as e:
        logger.warning(f"[Preprocess] Failed ({e}), using raw audio.")
        return src_path


# ── Whisper model ────────────────────────────────────────────────────────────

def get_model():
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
                logger.warning(f"Falling back to model '{FALLBACK_MODEL_SIZE}'")
                _model = WhisperModel(FALLBACK_MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
                logger.info("Fallback Faster-Whisper model loaded.")
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
            # Also pre-import preprocessing libs in background.
            await asyncio.to_thread(_ensure_preprocess_libs)
        except Exception as e:
            logger.error(f"STT warmup failed: {e}")

    asyncio.create_task(_warm())


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "stt",
        "model": MODEL_SIZE,
        "ready": _model is not None,
        "loading": _model_loading,
        "error": _model_error,
        "preprocessing": _nr is not None,
    }


# ── Transcription ────────────────────────────────────────────────────────────

# Per-segment thresholds. These gate individual Whisper segments before text
# is accumulated — much more precise than whole-file thresholds.
# Relaxed to avoid dropping correct but uncertain speech in noisy conditions.
_SEG_MIN_LOGPROB = -1.2        # more lenient; noisy audio naturally has lower confidence
_SEG_MAX_NO_SPEECH = 0.8       # only reject if Whisper is very sure it's not speech
_SEG_MIN_LOGPROB_STRICT = -1.8 # used when no_speech_prob is also elevated


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str | None = Form(default=None)):
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

    clean_path = None
    try:
        if _model is None and _model_loading:
            raise HTTPException(
                status_code=503,
                detail="STT model is still initializing. Please retry in a few moments.",
            )

        forced_lang = (language or "").strip().lower() or None
        if forced_lang == "auto":
            forced_lang = None

        def run_transcription(raw_path: str):
            model = get_model()
            start_time = time.time()

            # ── Stage 1: Denoise ──────────────────────────────────────────
            audio_path = _preprocess_audio(raw_path)

            # ── Stage 2: Whisper ──────────────────────────────────────────
            segments_iter, info = model.transcribe(
                audio_path,
                language=forced_lang,

                # Decoding quality - balanced for speed + accuracy
                beam_size=5,            # reasonable beam search
                best_of=5,              # 5 candidates (faster than 10)
                patience=1.0,           # default patience
                temperature=0,          # deterministic single-pass (fastest)

                # Noise robustness
                condition_on_previous_text=False,  # each segment decoded independently
                no_speech_threshold=0.6,           # Whisper's own silence gate (default)
                log_prob_threshold=-1.0,            # let per-segment filter do the heavy lifting
                compression_ratio_threshold=2.4,   # default; catches blatant repetition loops
                repetition_penalty=1.1,            # penalise recurring n-grams

                # Whisper-internal VAD — pre-screens the audio before decoding
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.45,              # relaxed; VAD tuned for messy/low-energy speech
                    "min_silence_duration_ms": 200, # shorter silences to catch natural pauses
                    "min_speech_duration_ms": 100,  # allow shorter utterances
                    "speech_pad_ms": 400,           # generous padding so word edges are captured
                },
            )

            # ── Stage 3: Per-segment confidence gate ─────────────────────
            kept_texts = []
            total_no_speech = 0.0
            total_logprob = 0.0
            n_segments = 0

            for seg in segments_iter:
                n_segments += 1
                total_no_speech += seg.no_speech_prob
                total_logprob += seg.avg_logprob

                seg_text = seg.text.strip()
                if not seg_text:
                    continue

                # Drop segment only if very high confidence it's not speech.
                # Relaxed thresholds to avoid dropping correct utterances in noisy audio.
                if seg.no_speech_prob > _SEG_MAX_NO_SPEECH:
                    logger.debug(
                        f"[Seg] Dropped (no_speech={seg.no_speech_prob:.2f}): {seg_text!r}"
                    )
                    continue

                if seg.avg_logprob < _SEG_MIN_LOGPROB_STRICT:
                    logger.debug(
                        f"[Seg] Dropped (logprob={seg.avg_logprob:.2f}): {seg_text!r}"
                    )
                    continue

                kept_texts.append(seg_text)

            raw_text = " ".join(kept_texts)

            # ── Stage 4: Hallucination filter ────────────────────────────
            avg_no_speech = total_no_speech / n_segments if n_segments else 1.0
            avg_logprob = total_logprob / n_segments if n_segments else -2.0
            full_text = _filter_hallucinations(raw_text, avg_no_speech, avg_logprob)

            duration = time.time() - start_time
            return full_text, info, duration, avg_logprob, avg_no_speech

        full_text, info, duration, avg_logprob, avg_no_speech = await asyncio.to_thread(
            run_transcription, tmp_path
        )

        logger.info(
            f"[STT] {file.filename} → {duration:.2f}s | "
            f"lang={info.language}({info.language_probability:.2f}) | "
            f"logprob={avg_logprob:.2f} | no_speech={avg_no_speech:.2f} | "
            f"text={full_text[:100]!r}"
        )

        return {
            "text": full_text,
            "language": info.language,
            "duration": round(duration, 2),
            "audio_duration_s": round(float(info.duration), 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        for path in (tmp_path, clean_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        # Clean up the preprocessed file too
        clean_candidate = tmp_path + "_clean.wav"
        if os.path.exists(clean_candidate):
            try:
                os.unlink(clean_candidate)
            except OSError:
                pass


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("STT_PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
