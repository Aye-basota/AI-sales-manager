"""Tests for app main module wiring."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class TestMainApp:
    def _client(self):
        # Avoid starting real background services during lifespan in tests.
        with patch("app.main.scheduler.start"):
            with patch("app.main.scheduler.shutdown"):
                with patch("app.main.start_bot"):
                    with patch("app.main.start_inbound_listeners"):
                        with TestClient(app) as client:
                            yield client

    def test_root_serves_site_index(self):
        # The root URL is served by StaticFiles from site/.
        client = next(self._client())
        response = client.get("/")
        assert response.status_code == 200
        assert "AI Sales Manager" in response.text or "Neural Lead" in response.text

    def test_routers_are_mounted(self):
        client = next(self._client())
        response = client.get("/docs")
        assert response.status_code == 200

    def test_validation_error_returns_400(self):
        client = next(self._client())
        response = client.post(
            "/telegram-accounts",
            json={"username": "missing_phone"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid request"
