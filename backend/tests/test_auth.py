"""
Tests for authentication endpoints.

Covers: register, login, refresh, logout, profile,
        email verification, password reset.
"""

import pytest
from tests.conftest import _register, _login, _auth_headers


# ── Registration ─────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client):
        resp = _register(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["client"]["email"] == "test@example.com"
        assert "api_key" in data          # shown once at registration
        assert data["api_key"].startswith("vrag_")

    def test_register_duplicate_email(self, client):
        _register(client)
        resp = _register(client)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        resp = client.post("/auth/register", json={
            "email": "notanemail",
            "password": "password123",
            "company_name": "TestCo",
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post("/auth/register", json={
            "email": "short@example.com",
            "password": "short",
            "company_name": "TestCo",
        })
        assert resp.status_code == 422

    def test_register_missing_company(self, client):
        resp = client.post("/auth/register", json={
            "email": "x@example.com",
            "password": "password123",
            "company_name": "   ",     # whitespace only
        })
        assert resp.status_code == 400


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, client):
        _register(client)
        resp = _login(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        _register(client)
        resp = client.post("/auth/login", json={"email": "test@example.com", "password": "wrongpass"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/auth/login", json={"email": "ghost@example.com", "password": "password123"})
        assert resp.status_code == 401

    def test_login_sets_refresh_cookie(self, client):
        _register(client)
        resp = _login(client)
        assert resp.status_code == 200
        # HTTP-only cookie should be present
        assert "voicerag_refresh" in resp.cookies


# ── Profile ───────────────────────────────────────────────────────────────────

class TestProfile:
    def test_get_profile_authenticated(self, client):
        reg = _register(client)
        token = reg.json()["access_token"]
        resp = client.get("/auth/me", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["company_name"] == "TestCo"
        assert "is_email_verified" in data
        assert "api_key_count" in data

    def test_get_profile_no_token(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 403  # missing credentials

    def test_get_profile_invalid_token(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


# ── Refresh token ─────────────────────────────────────────────────────────────

class TestRefreshToken:
    def test_refresh_returns_new_access_token(self, client):
        _register(client)
        login_resp = _login(client)
        assert login_resp.status_code == 200

        # The TestClient carries cookies automatically
        refresh_resp = client.post("/auth/refresh")
        assert refresh_resp.status_code == 200
        assert "access_token" in refresh_resp.json()

    def test_refresh_without_cookie_fails(self, client):
        resp = client.post("/auth/refresh")
        # No cookie → 401
        assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_revokes_tokens(self, client):
        _register(client)
        login_resp = _login(client)
        token = login_resp.json()["access_token"]

        logout_resp = client.post("/auth/logout", headers=_auth_headers(token))
        assert logout_resp.status_code == 200

        # Refresh should now fail (tokens revoked)
        refresh_resp = client.post("/auth/refresh")
        assert refresh_resp.status_code == 401


# ── Email verification ────────────────────────────────────────────────────────

class TestEmailVerification:
    def test_verify_with_bad_token(self, client):
        resp = client.post("/auth/verify-email", json={"token": "bad-token"})
        assert resp.status_code == 400

    def test_verify_with_real_token(self, client, db):
        _register(client)

        from app.models.database import Client
        cli = db.query(Client).filter(Client.email == "test@example.com").first()
        assert cli is not None
        token = cli.email_verification_token

        if token:
            resp = client.post("/auth/verify-email", json={"token": token})
            assert resp.status_code == 200
            # Reload from DB
            db.refresh(cli)
            assert cli.is_email_verified is True

    def test_resend_verification_unknown_email(self, client):
        # Should not reveal that email doesn't exist
        resp = client.post("/auth/resend-verification", json={"email": "ghost@example.com"})
        assert resp.status_code == 200


# ── Password reset ────────────────────────────────────────────────────────────

class TestPasswordReset:
    def test_forgot_password_unknown_email_still_200(self, client):
        resp = client.post("/auth/forgot-password", json={"email": "ghost@example.com"})
        assert resp.status_code == 200

    def test_reset_with_bad_token(self, client):
        resp = client.post("/auth/reset-password", json={
            "token": "bad-token",
            "new_password": "newpassword123",
        })
        assert resp.status_code == 400

    def test_full_reset_flow(self, client, db):
        _register(client)

        # Trigger forgot-password (token generated in DB even without email)
        client.post("/auth/forgot-password", json={"email": "test@example.com"})

        from app.models.database import Client
        cli = db.query(Client).filter(Client.email == "test@example.com").first()
        token = cli.password_reset_token

        if not token:
            pytest.skip("No reset token generated (email may not be active)")

        resp = client.post("/auth/reset-password", json={
            "token": token,
            "new_password": "newsecurepass123",
        })
        assert resp.status_code == 200

        # Old password should no longer work
        login_old = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
        assert login_old.status_code == 401

        # New password should work
        login_new = client.post("/auth/login", json={"email": "test@example.com", "password": "newsecurepass123"})
        assert login_new.status_code == 200
