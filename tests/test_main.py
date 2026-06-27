"""Tests for app main module wiring."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class TestMainApp:
    @staticmethod
    @contextmanager
    def _with_test_client():
        # Avoid starting real background services during lifespan in tests.
        with patch("app.main.scheduler.start"):
            with patch("app.main.scheduler.shutdown"):
                with patch("app.main.start_bot", return_value=AsyncMock()):
                    with patch("app.main.stop_bot", new=AsyncMock()):
                        with patch("app.main.start_inbound_listeners", return_value=AsyncMock()):
                            with patch("app.main.stop_inbound_listeners", new=AsyncMock()):
                                with patch("app.main.close_redis", new=AsyncMock()):
                                    with TestClient(app) as client:
                                        yield client

    def test_root_serves_site_index(self):
        # The root URL is served by StaticFiles from site/.
        with self._with_test_client() as client:
            response = client.get("/")
        assert response.status_code == 200
        assert "AI Sales Manager" in response.text or "Neural Lead" in response.text

    def test_routers_are_mounted(self):
        with self._with_test_client() as client:
            response = client.get("/docs")
        assert response.status_code == 200

    def test_validation_error_returns_400(self):
        with self._with_test_client() as client:
            response = client.post(
                "/telegram-accounts",
                json={"username": "missing_phone"},
            )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid request"
