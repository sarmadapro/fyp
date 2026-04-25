"""Force download Faster-Whisper large model."""
import os
import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# Setup CUDA DLLs (Windows)
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

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from faster_whisper import WhisperModel

print("Force-downloading Faster-Whisper large model...")
print(f"   Device: {os.getenv('STT_DEVICE', 'cpu')}")
print(f"   Compute: {os.getenv('STT_COMPUTE_TYPE', 'int8')}")

try:
    model = WhisperModel(
        "large",
        device=os.getenv("STT_DEVICE", "cuda"),
        compute_type=os.getenv("STT_COMPUTE_TYPE", "float16")
    )
    print("[OK] Large model downloaded and loaded successfully!")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    sys.exit(1)
