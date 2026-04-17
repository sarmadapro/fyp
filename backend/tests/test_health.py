"""
Basic smoke tests — health endpoints and system state.
"""


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "llm_provider" in data
        assert "llm_model" in data

    def test_docs_available(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_available(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200
