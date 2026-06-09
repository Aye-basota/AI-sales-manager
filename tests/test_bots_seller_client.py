"""Tests for the stub seller client and client pool."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bots.seller_client import ClientPool, SellerClient


class TestSellerClient:
    @pytest.mark.asyncio
    async def test_start_sets_started_flag(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        assert client._started is False
        await client.start()
        assert client._started is True
        await client.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_started_flag(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        await client.start()
        assert client._started is True
        await client.stop()
        assert client._started is False

    @pytest.mark.asyncio
    async def test_send_message_raises_when_not_initialized(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        with pytest.raises(RuntimeError, match="SellerClient not initialized"):
            await client.send_message(user_id=123, text="hello")

    @pytest.mark.asyncio
    async def test_send_message_applies_typing_delay(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        # Simulate an initialized Pyrogram client
        client._client = AsyncMock()
        client._client.send_message = AsyncMock(
            return_value=MagicMock(id=1, date=1, chat=MagicMock(id=123, type="private"), text="hello")
        )
        with patch("app.bots.seller_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client.send_message(user_id=123, text="hello", typing_delay_ms=500)
        mock_sleep.assert_awaited_once_with(0.5)
        assert result["text"] == "hello"

    @pytest.mark.asyncio
    async def test_ensure_connected_with_exponential_backoff(self):
        client = SellerClient(account_id="acc1", session_string="sess1", api_id=1, api_hash="hash")
        mock_client = MagicMock()
        mock_client.is_connected = False
        mock_client.start = AsyncMock()
        client._client = mock_client
        client._max_backoff = 2

        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", True):
            with patch("app.bots.seller_client.asyncio.sleep", new_callable=AsyncMock):
                await client._ensure_connected()

        mock_client.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_heartbeat_reconnects_on_disconnect(self):
        client = SellerClient(account_id="acc1", session_string="sess1", api_id=1, api_hash="hash")
        mock_client = MagicMock()
        mock_client.is_connected = False
        mock_client.start = AsyncMock()
        mock_client.stop = AsyncMock()
        client._client = mock_client
        client._heartbeat_interval = 0.05

        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", True):
            await client.start()
            await asyncio.sleep(0.15)
            await client.stop()

        assert mock_client.start.await_count >= 1

    @pytest.mark.asyncio
    async def test_with_reconnect_retries_on_connection_error(self):
        client = SellerClient(account_id="acc1", session_string="sess1", api_id=1, api_hash="hash")
        mock_client = MagicMock()
        mock_client.is_connected = False
        mock_client.start = AsyncMock()
        client._client = mock_client

        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("boom")
            return "success"

        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", True):
            result = await client._with_reconnect(failing_then_success)
        assert result == "success"
        assert call_count == 2
        mock_client.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_message_reconnects_on_connection_error(self):
        client = SellerClient(account_id="acc1", session_string="sess1", api_id=1, api_hash="hash")
        mock_client = MagicMock()
        mock_client.is_connected = False
        mock_client.start = AsyncMock()
        client._client = mock_client

        call_count = 0

        async def flaky_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("boom")
            return MagicMock(id=1, date=1, chat=MagicMock(id=123, type="private"), text="hello")

        mock_client.send_message = AsyncMock(side_effect=flaky_send)

        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", True):
            result = await client.send_message(user_id=123, text="hello")
        assert result["text"] == "hello"
        assert call_count == 2
        mock_client.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_cancels_heartbeat(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        await client.start()
        assert client._heartbeat_task is not None
        await client.stop()
        assert client._heartbeat_task is None


class TestClientPool:
    def test_register_and_get_client(self):
        pool = ClientPool()
        client = SellerClient(account_id="acc1", session_string="sess1")
        pool.register(client)
        assert pool.get_client("acc1") is client

    def test_get_client_returns_none_when_missing(self):
        pool = ClientPool()
        assert pool.get_client("missing") is None

    @pytest.mark.asyncio
    async def test_start_all_starts_registered_clients(self):
        pool = ClientPool()
        client1 = SellerClient(account_id="acc1", session_string="sess1")
        client2 = SellerClient(account_id="acc2", session_string="sess2")
        pool.register(client1)
        pool.register(client2)

        await pool.start_all()
        assert client1._started is True
        assert client2._started is True
        await pool.stop_all()

    @pytest.mark.asyncio
    async def test_stop_all_stops_registered_clients(self):
        pool = ClientPool()
        client1 = SellerClient(account_id="acc1", session_string="sess1")
        client2 = SellerClient(account_id="acc2", session_string="sess2")
        pool.register(client1)
        pool.register(client2)

        await pool.start_all()
        await pool.stop_all()
        assert client1._started is False
        assert client2._started is False

    @pytest.mark.asyncio
    async def test_start_all_logs_warning_when_empty(self):
        pool = ClientPool()
        with patch("app.bots.seller_client.logger.warning") as mock_warn:
            await pool.start_all()
        mock_warn.assert_called_once()
