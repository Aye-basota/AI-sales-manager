"""Tests for app main module wiring."""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import (
    app,
    _observe_background_task,
    _supervise_admin_bot,
    lifespan,
    unhandled_exception_handler,
)


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

    async def test_background_task_cancelled_and_finished_are_logged(self, caplog):
        async def wait_forever():
            await asyncio.Event().wait()

        async def finish():
            return "ok"

        with caplog.at_level("INFO"):
            cancelled = _observe_background_task(
                asyncio.create_task(wait_forever()), "cancelled_task"
            )
            cancelled.cancel()
            await asyncio.gather(cancelled, return_exceptions=True)
            await asyncio.sleep(0)

            finished = _observe_background_task(
                asyncio.create_task(finish()), "finished_task"
            )
            await finished
            await asyncio.sleep(0)

        assert "Background task cancelled_task cancelled" in caplog.text
        assert "Background task finished_task finished" in caplog.text

    def test_background_task_exception_cancelled_error_branch(self, caplog):
        class FakeTask:
            def cancelled(self):
                return False

            def exception(self):
                raise asyncio.CancelledError

            def add_done_callback(self, callback):
                callback(self)

        with caplog.at_level("INFO"):
            assert _observe_background_task(FakeTask(), "fake_task") is not None

        assert "Background task fake_task cancelled" in caplog.text

    async def test_supervise_admin_bot_start_once_when_not_configured(self):
        with (
            patch("app.main.is_admin_bot_configured", return_value=False),
            patch("app.main.start_bot", new_callable=AsyncMock) as mock_start,
        ):
            await _supervise_admin_bot()

        mock_start.assert_awaited_once()

    async def test_supervise_admin_bot_logs_crash_and_restarts_until_cancelled(
        self, caplog
    ):
        with (
            patch("app.main.is_admin_bot_configured", return_value=True),
            patch(
                "app.main.start_bot",
                new=AsyncMock(side_effect=[RuntimeError("polling down"), asyncio.CancelledError()]),
            ) as mock_start,
            patch("app.main.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            with caplog.at_level("ERROR"):
                try:
                    await _supervise_admin_bot()
                except asyncio.CancelledError:
                    pass

        assert mock_start.await_count == 2
        mock_sleep.assert_awaited_once_with(5)
        assert "Admin bot polling crashed" in caplog.text

    async def test_lifespan_signal_fallback_and_shutdown_cancels_tasks(self):
        async def never():
            await asyncio.Event().wait()

        fake_loop = MagicMock()
        fake_loop.add_signal_handler.side_effect = RuntimeError("signals unsupported")
        background_thread = SimpleNamespace(name="worker")
        main_thread = SimpleNamespace(name="main")

        with (
            patch("app.main.threading.current_thread", return_value=background_thread),
            patch("app.main.threading.main_thread", return_value=main_thread),
        ):
            # Different objects skip signal branch; now assert full lifecycle still works.
            with (
                patch("app.main.scheduler.start"),
                patch("app.main.scheduler.shutdown"),
                patch("app.main._supervise_admin_bot", side_effect=never),
                patch("app.main.start_inbound_listeners", side_effect=never),
                patch("app.main.stop_inbound_listeners", new_callable=AsyncMock),
                patch("app.main.stop_bot", new_callable=AsyncMock),
                patch("app.main.close_redis", new_callable=AsyncMock),
            ):
                async with lifespan(app):
                    pass
                await asyncio.sleep(0)

        same_thread = SimpleNamespace(name="main")
        with (
            patch("app.main.threading.current_thread", return_value=same_thread),
            patch("app.main.threading.main_thread", return_value=same_thread),
            patch("app.main.asyncio.get_running_loop", return_value=fake_loop),
            patch("app.main.signal.signal") as mock_signal,
            patch("app.main.scheduler.start"),
            patch("app.main.scheduler.shutdown"),
            patch("app.main._supervise_admin_bot", side_effect=never),
            patch("app.main.start_inbound_listeners", side_effect=never),
            patch("app.main.stop_inbound_listeners", new_callable=AsyncMock),
            patch("app.main.stop_bot", new_callable=AsyncMock),
            patch("app.main.close_redis", new_callable=AsyncMock),
        ):
            async with lifespan(app):
                pass
            await asyncio.sleep(0)

        assert fake_loop.add_signal_handler.called
        assert mock_signal.call_count == 2
        fallback_handler = mock_signal.call_args_list[0].args[1]
        fallback_handler(15, None)

    async def test_unhandled_exception_returns_stable_json(self, caplog):
        request = SimpleNamespace(method="GET", url=SimpleNamespace(path="/boom"))
        exc = RuntimeError("private details")

        with caplog.at_level("ERROR"):
            response = await unhandled_exception_handler(request, exc)

        assert response.status_code == 500
        assert response.body == b'{"detail":"Internal server error"}'
        assert "Unhandled API error for GET /boom" in caplog.text
