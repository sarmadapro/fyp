"""
Unit tests for core services (auth_service, document_service helpers).
These tests run against an in-memory DB and do NOT call external APIs.
"""

import pytest
from datetime import datetime, timedelta, timezone

from tests.conftest import TestingSessionLocal
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    register_client,
    authenticate_client,
    set_email_verification_token,
    verify_email_token,
    set_password_reset_token,
    reset_password_with_token,
    create_refresh_token,
    validate_and_rotate_refresh_token,
    revoke_all_refresh_tokens,
)
from app.models.database import Client, RefreshToken


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Password helpers ─────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("mysecret")
        assert verify_password("mysecret", h) is True

    def test_wrong_password_rejected(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_hashes_are_different_each_time(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


# ── JWT ──────────────────────────────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token({"sub": "abc-123"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "abc-123"
        assert payload["type"] == "access"

    def test_expired_token_returns_none(self):
        token = create_access_token({"sub": "x"}, expires_delta=timedelta(seconds=-1))
        assert decode_access_token(token) is None

    def test_invalid_token_returns_none(self):
        assert decode_access_token("not.a.token") is None


# ── Client CRUD ──────────────────────────────────────────────────────────────

class TestClientCRUD:
    def test_register_and_authenticate(self, db):
        cli = register_client(db, "user@test.com", "pass1234!", "Acme", "Alice")
        assert cli.id is not None
        assert cli.email == "user@test.com"

        auth_cli = authenticate_client(db, "user@test.com", "pass1234!")
        assert auth_cli is not None
        assert auth_cli.id == cli.id

    def test_duplicate_email_raises(self, db):
        register_client(db, "dup@test.com", "pass1234!", "Co", "Bob")
        with pytest.raises(ValueError, match="already exists"):
            register_client(db, "dup@test.com", "pass1234!", "Co2", "Carol")

    def test_authenticate_wrong_password(self, db):
        register_client(db, "check@test.com", "rightpass!", "X")
        assert authenticate_client(db, "check@test.com", "wrongpass") is None

    def test_authenticate_unknown_email(self, db):
        assert authenticate_client(db, "nobody@test.com", "any") is None

    def test_inactive_client_rejected(self, db):
        cli = register_client(db, "inactive@test.com", "pass1234!", "Y")
        cli.is_active = False
        db.commit()
        assert authenticate_client(db, "inactive@test.com", "pass1234!") is None


# ── Email verification ────────────────────────────────────────────────────────

class TestEmailVerification:
    def test_token_set_and_cleared(self, db):
        cli = register_client(db, "verify@test.com", "pass1234!", "Z")
        token = set_email_verification_token(db, cli)
        assert token
        assert cli.email_verification_token == token

        result = verify_email_token(db, token)
        assert result is not None
        assert result.is_email_verified is True
        assert result.email_verification_token is None

    def test_bad_token_returns_none(self, db):
        assert verify_email_token(db, "fake-token") is None

    def test_expired_token_rejected(self, db):
        cli = register_client(db, "exp@test.com", "pass1234!", "W")
        token = set_email_verification_token(db, cli)
        # Manually expire it
        cli.email_verification_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
        assert verify_email_token(db, token) is None


# ── Password reset ────────────────────────────────────────────────────────────

class TestPasswordReset:
    def test_full_reset_flow(self, db):
        cli = register_client(db, "reset@test.com", "oldpass!", "V")
        token = set_password_reset_token(db, cli)
        assert token

        result = reset_password_with_token(db, token, "newpass!")
        assert result is not None

        # Old password no longer works
        assert authenticate_client(db, "reset@test.com", "oldpass!") is None
        # New password works
        assert authenticate_client(db, "reset@test.com", "newpass!") is not None

    def test_reset_token_consumed_once(self, db):
        cli = register_client(db, "once@test.com", "pass1234!", "U")
        token = set_password_reset_token(db, cli)
        reset_password_with_token(db, token, "newpass!")
        # Second use must fail
        assert reset_password_with_token(db, token, "another") is None


# ── Refresh tokens ────────────────────────────────────────────────────────────

class TestRefreshTokens:
    def test_create_validate_rotate(self, db):
        cli = register_client(db, "refresh@test.com", "pass1234!", "T")
        raw = create_refresh_token(db, cli.id, "TestAgent", "127.0.0.1")
        assert raw

        returned_client, new_raw = validate_and_rotate_refresh_token(db, raw)
        assert returned_client is not None
        assert returned_client.id == cli.id
        assert new_raw is not None
        assert new_raw != raw  # token must be rotated

    def test_used_token_rejected(self, db):
        cli = register_client(db, "used@test.com", "pass1234!", "S")
        raw = create_refresh_token(db, cli.id)
        validate_and_rotate_refresh_token(db, raw)  # use it once
        # Second use (replay attack) must fail
        c, nr = validate_and_rotate_refresh_token(db, raw)
        assert c is None

    def test_revoke_all(self, db):
        cli = register_client(db, "revoke@test.com", "pass1234!", "R")
        raw = create_refresh_token(db, cli.id)
        revoke_all_refresh_tokens(db, cli.id)

        c, nr = validate_and_rotate_refresh_token(db, raw)
        assert c is None


# ── Document service cache ────────────────────────────────────────────────────

class TestClientDocumentServiceCache:
    def test_get_or_create_returns_same_instance(self):
        from app.services.document_service import ClientDocumentService
        ClientDocumentService.invalidate("cache-test-client")

        svc1 = ClientDocumentService.get_or_create("cache-test-client")
        svc2 = ClientDocumentService.get_or_create("cache-test-client")
        assert svc1 is svc2

    def test_invalidate_returns_fresh_instance(self):
        from app.services.document_service import ClientDocumentService
        ClientDocumentService.invalidate("cache-test-client-2")

        svc1 = ClientDocumentService.get_or_create("cache-test-client-2")
        ClientDocumentService.invalidate("cache-test-client-2")
        svc2 = ClientDocumentService.get_or_create("cache-test-client-2")
        assert svc1 is not svc2
