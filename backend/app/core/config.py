"""
Application configuration loaded from environment variables.
Designed for SaaS extensibility — all settings centralized here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Try multiple paths to find .env file
_possible_env_paths = [
    Path(__file__).resolve().parent.parent.parent.parent / ".env",  # From backend/app/core/config.py to project root
    Path(__file__).resolve().parent.parent.parent / ".env",  # One level up (in case structure is different)
    Path.cwd() / ".env",  # Current working directory
    Path.cwd().parent / ".env",  # Parent of current working directory
]

_env_loaded = False
for _env_path in _possible_env_paths:
    if _env_path.exists():
        load_dotenv(_env_path)
        print(f"[CONFIG] ✓ Loaded .env from: {_env_path}")
        _env_loaded = True
        break

if not _env_loaded:
    print("[CONFIG] ⚠ WARNING: .env file not found in any expected location!")
    print("[CONFIG] Tried:")
    for path in _possible_env_paths:
        print(f"[CONFIG]   - {path}")
    # Try loading from environment anyway
    load_dotenv()


class Settings:
    """Central configuration for the application."""

    # --- Server ---
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # --- Groq LLM ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # --- RAG ---
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "8"))

    # --- File Storage ---
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
    INDEX_DIR: Path = Path(os.getenv("INDEX_DIR", "./data/indices"))

    # --- Microservices ---
    STT_SERVICE_URL: str = os.getenv("STT_SERVICE_URL", "http://localhost:8001")
    TTS_SERVICE_URL: str = os.getenv("TTS_SERVICE_URL", "http://localhost:8002")

    def __init__(self):
        # Ensure directories exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        # Validate critical settings
        if not self.GROQ_API_KEY:
            print("[CONFIG] WARNING: GROQ_API_KEY is not set!")
            print("[CONFIG] Please add your Groq API key to the .env file")
        else:
            print(f"[CONFIG] GROQ_API_KEY loaded: {self.GROQ_API_KEY[:20]}...")


settings = Settings()

# Print loaded configuration on import
print(f"[CONFIG] Backend Host: {settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
print(f"[CONFIG] LLM Model: {settings.LLM_MODEL}")
print(f"[CONFIG] Embedding Model: {settings.EMBEDDING_MODEL}")
