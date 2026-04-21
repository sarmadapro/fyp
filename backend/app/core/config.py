"""
Application configuration loaded from environment variables.
Designed for SaaS extensibility — all settings centralized here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Try multiple paths to find .env file
_possible_env_paths = [
    Path(__file__).resolve().parent.parent.parent.parent / ".env",  # project root
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path.cwd() / ".env",
    Path.cwd().parent / ".env",
]

_env_loaded = False
for _env_path in _possible_env_paths:
    if _env_path.exists():
        load_dotenv(_env_path)
        print(f"[CONFIG] Loaded .env from: {_env_path}")
        _env_loaded = True
        break

if not _env_loaded:
    print("[CONFIG] WARNING: .env file not found in any expected location!")
    load_dotenv()


class Settings:
    """Central configuration for the application."""

    # --- Server ---
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:3000"
    ).split(",")

    # --- LLM Configuration ---
    # Priority: DeepSeek → Groq → Ollama
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "qwen2.5:0.5b"))

    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # Resolved provider (computed in __init__)
    LLM_PROVIDER: str = ""
    LLM_MODEL: str = ""

    # --- RAG ---
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "8"))

    # --- File Storage ---
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
    INDEX_DIR: Path = Path(os.getenv("INDEX_DIR", "./data/indices"))
    CLIENT_DATA_DIR: Path = Path(os.getenv("CLIENT_DATA_DIR", "./data/clients"))

    # --- Microservices ---
    STT_SERVICE_URL: str = os.getenv("STT_SERVICE_URL", "http://localhost:8001")
    TTS_SERVICE_URL: str = os.getenv("TTS_SERVICE_URL", "http://localhost:8002")

    # --- Auth ---
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "voicerag-dev-secret-change-in-production-2024")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # --- Email ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@voicerag.ai")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # set to postgres url in production

    def __init__(self):
        # Ensure directories exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self.CLIENT_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Resolve LLM provider with priority:
        # 1. DeepSeek (if DEEPSEEK_API_KEY present) — primary, 128K context window
        # 2. Groq (if GROQ_API_KEY present) — fast fallback
        # 3. Ollama (default) — local offline fallback
        _deepseek_key_valid = (
            bool(self.DEEPSEEK_API_KEY)
            and self.DEEPSEEK_API_KEY not in ("your_deepseek_api_key_here", "")
        )
        _groq_key_valid = (
            bool(self.GROQ_API_KEY)
            and self.GROQ_API_KEY not in ("your_groq_api_key_here", "")
        )

        if _deepseek_key_valid:
            self.LLM_PROVIDER = "deepseek"
            self.LLM_MODEL = self.DEEPSEEK_MODEL
            print(f"[CONFIG] LLM: DeepSeek ({self.DEEPSEEK_MODEL}) — key detected")
        elif _groq_key_valid:
            self.LLM_PROVIDER = "groq"
            self.LLM_MODEL = self.GROQ_MODEL
            print(f"[CONFIG] LLM: Groq ({self.GROQ_MODEL}) — DeepSeek key missing, using Groq fallback")
        else:
            self.LLM_PROVIDER = "ollama"
            self.LLM_MODEL = self.OLLAMA_MODEL
            print(f"[CONFIG] LLM: Ollama @ {self.OLLAMA_BASE_URL} ({self.OLLAMA_MODEL}) — no API keys found")

        print(f"[CONFIG] Backend: {self.BACKEND_HOST}:{self.BACKEND_PORT}")
        print(f"[CONFIG] Embedding: {self.EMBEDDING_MODEL}")


settings = Settings()
