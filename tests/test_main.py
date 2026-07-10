"""Tests for app main module wiring."""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app, _observe_background_task, unhandled_exception_handler


class TestMainApp:
    @staticmethod
    @contextmanager
    def _with_test_client():
        # Avoid starting real background services during lifespan in tests.
        with patch("app.main.scheduler.start"):
            with patch("app.main.scheduler.shutdown"):
                with patch("app.main.start_bot", return_value=AsyncMock()):
                    with patch("app.main.stop_bot", new=AsyncMock()):
                        with patch(
                            "app.main.start_inbound_listeners", return_value=AsyncMock()
                        ):
                            with patch(
                                "app.main.stop_inbound_listeners", new=AsyncMock()
                            ):
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

    async def test_background_task_failure_is_logged(self, caplog):
        async def fail():
            raise RuntimeError("startup boom")

        with caplog.at_level("ERROR"):
            task = _observe_background_task(asyncio.create_task(fail()), "test_task")
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.sleep(0)

        assert "Background task test_task failed" in caplog.text
        assert "startup boom" in caplog.text

    async def test_unhandled_exception_returns_stable_json(self, caplog):
        request = SimpleNamespace(method="GET", url=SimpleNamespace(path="/boom"))
        exc = RuntimeError("private details")

        with caplog.at_level("ERROR"):
            response = await unhandled_exception_handler(request, exc)

        assert response.status_code == 500
        assert response.body == b'{"detail":"Internal server error"}'
        assert "Unhandled API error for GET /boom" in caplog.text
