"""
pytest configuration and shared fixtures.

Uses a temp-file SQLite database (not :memory:) so all connections see the
same tables.  SQLite :memory: creates a fresh empty DB per connection, which
breaks fixtures that open separate sessions.

The DATABASE_URL env var is set BEFORE any app code is imported so the app's
own engine points at the same temp file.
"""

import os
import tempfile
import atexit
import pytest

# ── Create a temp SQLite file and configure it BEFORE any app imports ────────
_db_fd, _db_path = tempfile.mkstemp(suffix="_test.db")
os.close(_db_fd)

os.environ["DATABASE_URL"]   = f"sqlite:///{_db_path}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-ci-only"
os.environ["LLM_PROVIDER"]   = "ollama"
os.environ["OLLAMA_MODEL"]   = "test-model"
os.environ["SMTP_USER"]      = ""   # disable real emails
os.environ["SMTP_PASSWORD"]  = ""

# Clean up the temp file when the process exits (best-effort on Windows)
def _cleanup_db():
    try:
        if os.path.exists(_db_path):
            os.unlink(_db_path)
    except OSError:
        pass  # Windows may hold the file open; temp dir cleaned by OS anyway
atexit.register(_cleanup_db)

# ── Now import app code (DATABASE_URL is already set) ────────────────────────
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import engine, Base, get_db
from main import app

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the entire test session."""
    from app.models.database import Client, APIKey, RefreshToken  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    """Delete all rows between tests to guarantee isolation."""
    from app.models.database import Client, APIKey, RefreshToken
    yield
    db = TestingSessionLocal()
    try:
        db.query(RefreshToken).delete()
        db.query(APIKey).delete()
        db.query(Client).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture
def client():
    """FastAPI TestClient with the test DB injected."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    """Raw DB session for direct assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register(client, email="test@example.com", password="password123",
               company="TestCo", full_name="Test User"):
    return client.post("/auth/register", json={
        "email": email,
        "password": password,
        "company_name": company,
        "full_name": full_name,
    })


def _login(client, email="test@example.com", password="password123"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
