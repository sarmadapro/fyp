"""
Tests for API key management endpoints.
"""

import pytest
from tests.conftest import _register, _auth_headers


def _get_token(client) -> str:
    resp = _register(client)
    return resp.json()["access_token"]


class TestAPIKeys:
    def test_list_keys_authenticated(self, client):
        token = _get_token(client)
        resp = client.get("/api-keys", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # One default key created at registration
        assert len(data) == 1

    def test_create_key(self, client):
        token = _get_token(client)
        resp = client.post("/api-keys", json={"name": "Production Key"}, headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "full_key" in data
        assert data["full_key"].startswith("vrag_")

    def test_revoke_key(self, client):
        token = _get_token(client)
        # Create an extra key
        create_resp = client.post("/api-keys", json={"name": "TempKey"}, headers=_auth_headers(token))
        assert create_resp.status_code == 200
        key_id = create_resp.json()["id"]

        revoke_resp = client.delete(f"/api-keys/{key_id}", headers=_auth_headers(token))
        assert revoke_resp.status_code == 200

        # Key should be marked inactive (list returns all keys, active and revoked)
        list_resp = client.get("/api-keys", headers=_auth_headers(token))
        keys_by_id = {k["id"]: k for k in list_resp.json()}
        assert key_id in keys_by_id
        assert keys_by_id[key_id]["is_active"] is False

    def test_cannot_exceed_max_keys(self, client):
        token = _get_token(client)
        # 1 default key; create 4 more = 5 total (max)
        for i in range(4):
            r = client.post("/api-keys", json={"name": f"Key {i}"}, headers=_auth_headers(token))
            assert r.status_code == 200

        # 6th key should fail
        r = client.post("/api-keys", json={"name": "One too many"}, headers=_auth_headers(token))
        assert r.status_code == 400

    def test_list_unauthenticated(self, client):
        resp = client.get("/api-keys")
        assert resp.status_code == 403
