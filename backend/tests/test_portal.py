"""
Tests for the client portal endpoints (document management + chat).

Document upload tests use a real tiny PDF/TXT file created in-memory
so they don't depend on any files on disk.
"""

import io
import pytest
from tests.conftest import _register, _auth_headers


def _get_token(client) -> str:
    return _register(client).json()["access_token"]


def _txt_file(content: str = "Hello world. This is test content. It talks about bananas."):
    return ("test.txt", io.BytesIO(content.encode()), "text/plain")


class TestDocumentStatus:
    def test_status_no_document(self, client):
        token = _get_token(client)
        resp = client.get("/portal/document/status", headers=_auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["has_document"] is False

    def test_status_unauthenticated(self, client):
        resp = client.get("/portal/document/status")
        assert resp.status_code == 403


class TestDocumentUpload:
    def test_upload_txt(self, client):
        token = _get_token(client)
        name, file_obj, mime = _txt_file()
        resp = client.post(
            "/portal/document/upload",
            files={"file": (name, file_obj, mime)},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_name"] == "test.txt"
        assert data["chunk_count"] > 0

    def test_upload_unsupported_type(self, client):
        token = _get_token(client)
        resp = client.post(
            "/portal/document/upload",
            files={"file": ("bad.exe", io.BytesIO(b"binary"), "application/octet-stream")},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 400

    def test_upload_replaces_previous(self, client):
        token = _get_token(client)
        headers = _auth_headers(token)

        # First upload
        name, f, mime = _txt_file("First document about cats.")
        resp1 = client.post("/portal/document/upload", files={"file": (name, f, mime)}, headers=headers)
        assert resp1.status_code == 200

        # Second upload
        name2, f2, mime2 = _txt_file("Second document about dogs.")
        resp2 = client.post("/portal/document/upload", files={"file": ("test2.txt", f2, mime2)}, headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["document_name"] == "test2.txt"

        # Status should reflect the new document only
        status = client.get("/portal/document/status", headers=headers).json()
        assert status["document_name"] == "test2.txt"
        assert status["has_document"] is True

    def test_upload_unauthenticated(self, client):
        name, f, mime = _txt_file()
        resp = client.post("/portal/document/upload", files={"file": (name, f, mime)})
        assert resp.status_code == 403


class TestDocumentDelete:
    def test_delete_existing_document(self, client):
        token = _get_token(client)
        headers = _auth_headers(token)

        name, f, mime = _txt_file()
        client.post("/portal/document/upload", files={"file": (name, f, mime)}, headers=headers)

        resp = client.delete("/portal/document/delete", headers=headers)
        assert resp.status_code == 200

        status = client.get("/portal/document/status", headers=headers).json()
        assert status["has_document"] is False

    def test_delete_no_document(self, client):
        token = _get_token(client)
        resp = client.delete("/portal/document/delete", headers=_auth_headers(token))
        assert resp.status_code == 404


class TestPortalChat:
    def test_chat_no_document(self, client):
        token = _get_token(client)
        resp = client.post(
            "/portal/chat",
            json={"question": "What is in the document?"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        # Should politely say no doc uploaded
        assert "upload" in data["answer"].lower() or "document" in data["answer"].lower()

    def test_chat_tenant_isolation(self, client):
        """Two clients must never see each other's data."""
        # Client A
        reg_a = _register(client, email="a@example.com")
        token_a = reg_a.json()["access_token"]
        name, f, mime = _txt_file("Client A document about rockets.")
        client.post("/portal/document/upload", files={"file": (name, f, mime)}, headers=_auth_headers(token_a))

        # Client B
        reg_b = _register(client, email="b@example.com")
        token_b = reg_b.json()["access_token"]

        # B has no doc — must not see A's content
        resp_b = client.get("/portal/document/status", headers=_auth_headers(token_b))
        assert resp_b.json()["has_document"] is False


class TestPortalChatStream:
    def test_stream_no_document(self, client):
        token = _get_token(client)
        resp = client.post(
            "/portal/chat/stream",
            json={"question": "Hello?"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
