"""Tests for the stub seller client and client pool."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.bots.seller_client import ClientPool, SellerClient


class TestSellerClient:
    @pytest.mark.asyncio
    async def test_start_sets_started_flag(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        assert client._started is False
        await client.start()
        assert client._started is True

    @pytest.mark.asyncio
    async def test_stop_clears_started_flag(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        await client.start()
        assert client._started is True
        await client.stop()
        assert client._started is False

    @pytest.mark.asyncio
    async def test_send_message_returns_mock_dict(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        result = await client.send_message(user_id=123, text="hello")
        assert isinstance(result, dict)
        assert result["chat"]["id"] == 123
        assert result["text"] == "hello"
        assert "message_id" in result
        assert "date" in result

    @pytest.mark.asyncio
    async def test_send_message_applies_typing_delay(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        with patch("app.bots.seller_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client.send_message(user_id=123, text="hello", typing_delay_ms=500)
        mock_sleep.assert_awaited_once_with(0.5)
        assert result["text"] == "hello"


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
