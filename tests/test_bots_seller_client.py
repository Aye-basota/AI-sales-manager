"""Tests for the stub seller client and client pool."""

import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

import app.bots.seller_client as seller_client_module
from app.bots.seller_client import ClientPool, SellerClient, thinking_delay, typing_delay_for


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
            return_value=MagicMock(
                id=1, date=1, chat=MagicMock(id=123, type="private"), text="hello"
            )
        )
        with patch(
            "app.bots.seller_client.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            result = await client.send_message(
                user_id=123, text="hello", typing_delay_ms=500
            )
        mock_sleep.assert_awaited_once_with(0.5)
        assert result["text"] == "hello"

    @pytest.mark.asyncio
    async def test_ensure_connected_with_exponential_backoff(self):
        client = SellerClient(
            account_id="acc1", session_string="sess1", api_id=1, api_hash="hash"
        )
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
    async def test_ensure_connected_initializes_already_connected_client(self):
        client = SellerClient(
            account_id="acc1", session_string="sess1", api_id=1, api_hash="hash"
        )
        mock_client = MagicMock(is_connected=True)

        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", True):
            with patch.object(client, "_init_client", return_value=mock_client):
                await client._ensure_connected()

        assert client._client is mock_client
        mock_client.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_heartbeat_reconnects_on_disconnect(self):
        client = SellerClient(
            account_id="acc1", session_string="sess1", api_id=1, api_hash="hash"
        )
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
        client = SellerClient(
            account_id="acc1", session_string="sess1", api_id=1, api_hash="hash"
        )
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
        client = SellerClient(
            account_id="acc1", session_string="sess1", api_id=1, api_hash="hash"
        )
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
            return MagicMock(
                id=1, date=1, chat=MagicMock(id=123, type="private"), text="hello"
            )

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

    @pytest.mark.asyncio
    async def test_stop_logs_client_stop_errors(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        client._client.stop = AsyncMock(side_effect=RuntimeError("stop failed"))

        with patch("app.bots.seller_client.logger.warning") as mock_warning:
            await client.stop()

        mock_warning.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_connected_returns_when_pyrogram_unavailable(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", False):
            await client._ensure_connected()

        assert client._client is None

    @pytest.mark.asyncio
    async def test_ensure_connected_retries_after_start_failure(self):
        client = SellerClient(
            account_id="acc1", session_string="sess1", api_id=1, api_hash="hash"
        )
        mock_client = MagicMock()
        mock_client.is_connected = False
        mock_client.start = AsyncMock(side_effect=[RuntimeError("boom"), None])
        client._client = mock_client

        with (
            patch("app.bots.seller_client._PYROGRAM_AVAILABLE", True),
            patch("app.bots.seller_client.asyncio.sleep", new_callable=AsyncMock),
        ):
            await client._ensure_connected()

        assert mock_client.start.await_count == 2

    @pytest.mark.asyncio
    async def test_heartbeat_breaks_when_stop_event_is_set(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._heartbeat_interval = 10
        task = asyncio.create_task(client._heartbeat_loop())
        await asyncio.sleep(0)
        client._stop_event.set()

        await asyncio.wait_for(task, timeout=1)

    @pytest.mark.asyncio
    async def test_heartbeat_logs_unexpected_errors(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._heartbeat_interval = 0.01
        calls = 0

        def broken_is_connected():
            nonlocal calls
            calls += 1
            client._stop_event.set()
            raise RuntimeError("heartbeat broken")

        client._client = MagicMock()
        client._is_connected = broken_is_connected

        with patch("app.bots.seller_client.logger.warning") as mock_warning:
            await client._heartbeat_loop()

        assert calls == 1
        mock_warning.assert_called()


class TestSellerClientHelpers:
    def test_delay_wrappers_delegate_to_humanizer(self):
        with patch(
            "app.bots.seller_client.calculate_typing_delay", return_value=1234
        ) as mock_typing:
            assert typing_delay_for("hello", chars_per_min=(100, 100)) == 1234
        mock_typing.assert_called_once_with("hello", chars_per_min=(100, 100))

        with patch(
            "app.bots.seller_client.calculate_thinking_delay", return_value=5000
        ) as mock_thinking:
            assert thinking_delay(min_sec=1, max_sec=2) == 5000
        mock_thinking.assert_called_once_with(min_sec=1, max_sec=2)

    def test_parse_proxy_returns_none_for_empty_url(self):
        from app.bots.seller_client import _parse_proxy

        assert _parse_proxy(None) is None
        assert _parse_proxy("") is None

    def test_parse_proxy_parses_socks5_url(self):
        from app.bots.seller_client import _parse_proxy

        proxy = _parse_proxy("socks5://user:pass@proxy.example.com:1080")
        assert proxy["scheme"] == "socks5"
        assert proxy["hostname"] == "proxy.example.com"
        assert proxy["port"] == 1080
        assert proxy["username"] == "user"
        assert proxy["password"] == "pass"

    def test_parse_proxy_ignores_unsupported_scheme(self):
        from app.bots.seller_client import _parse_proxy

        assert _parse_proxy("https://proxy.example.com:8080") is None

    def test_decrypt_session_returns_plaintext_without_fernet(self):
        client = SellerClient(account_id="acc1", session_string="plain")
        client._fernet = None

        assert client._decrypt_session() == "plain"

    def test_init_session_encryption_key_from_settings_and_invalid_key(self, monkeypatch):
        key = Fernet.generate_key()
        monkeypatch.delenv("SESSION_ENCRYPTION_KEY", raising=False)
        monkeypatch.setattr(
            "app.config.get_settings",
            lambda: MagicMock(session_encryption_key=key.decode()),
        )
        client = SellerClient(account_id="acc1", session_string="plain")
        assert client._fernet is not None

        monkeypatch.setenv("SESSION_ENCRYPTION_KEY", "bad-key")
        with patch("app.bots.seller_client.logger.warning") as mock_warning:
            bad_client = SellerClient(account_id="acc2", session_string="plain")
        assert bad_client._fernet is None
        mock_warning.assert_called()

    def test_init_session_encryption_settings_failure_falls_back_to_plaintext(
        self, monkeypatch
    ):
        monkeypatch.delenv("SESSION_ENCRYPTION_KEY", raising=False)

        def broken_settings():
            raise RuntimeError("settings failed")

        monkeypatch.setattr("app.config.get_settings", broken_settings)
        client = SellerClient(account_id="acc1", session_string="plain")

        assert client._fernet is None

    def test_decrypt_session_uses_configured_fernet_and_falls_back_on_error(self):
        key = Fernet.generate_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(b"secret").decode()
        client = SellerClient(account_id="acc1", session_string=encrypted)
        client._fernet = fernet

        assert client._decrypt_session() == "secret"

        client.session_string = "not-a-token"
        assert client._decrypt_session() == "not-a-token"

    def test_init_client_requires_api_credentials(self):
        client = SellerClient(account_id="acc1", session_string="sess1")

        assert client._init_client() is None

    def test_init_client_builds_pyrogram_client_with_proxy(self):
        client = SellerClient(
            account_id="acc1",
            session_string="sess1",
            proxy_url="http://proxy.example.com:8080",
            api_id=123,
            api_hash="hash",
            no_updates=False,
        )
        with patch("app.bots.seller_client.Client") as mock_client_cls:
            result = client._init_client()

        assert result is mock_client_cls.return_value
        kwargs = mock_client_cls.call_args.kwargs
        assert kwargs["name"] == "seller_acc1"
        assert kwargs["api_id"] == 123
        assert kwargs["api_hash"] == "hash"
        assert kwargs["session_string"] == "sess1"
        assert kwargs["proxy"]["hostname"] == "proxy.example.com"
        assert kwargs["no_updates"] is False

    def test_is_connected_false_without_client_or_pyrogram(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        assert client._is_connected() is False
        client._client = MagicMock(is_connected=True)
        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", False):
            assert client._is_connected() is False

    @pytest.mark.asyncio
    async def test_set_typing_without_client_logs_debug(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        with patch("app.bots.seller_client.logger.debug") as mock_debug:
            await client.set_typing(user_id=123)
        mock_debug.assert_called()

    @pytest.mark.asyncio
    async def test_set_typing_uses_chat_action(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        client._client.send_chat_action = AsyncMock()

        await client.set_typing(user_id=123)

        client._client.send_chat_action.assert_awaited_once()
        assert client._client.send_chat_action.call_args.kwargs["chat_id"] == 123

    @pytest.mark.asyncio
    async def test_set_typing_logs_reconnect_errors(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        with patch.object(
            client, "_with_reconnect", new=AsyncMock(side_effect=RuntimeError("bad"))
        ):
            with patch("app.bots.seller_client.logger.warning") as mock_warning:
                await client.set_typing(user_id=123)
        mock_warning.assert_called()

    @pytest.mark.asyncio
    async def test_set_online_without_client_logs_debug(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        with patch("app.bots.seller_client.logger.debug") as mock_debug:
            await client.set_online()
        mock_debug.assert_called()

    @pytest.mark.asyncio
    async def test_set_online_invokes_update_status_when_client_exists(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        client._client.invoke = AsyncMock()

        await client.set_online()

        client._client.invoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_online_logs_reconnect_errors(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        with patch.object(
            client, "_with_reconnect", new=AsyncMock(side_effect=RuntimeError("bad"))
        ):
            with patch("app.bots.seller_client.logger.warning") as mock_warning:
                await client.set_online()
        mock_warning.assert_called()

    @pytest.mark.asyncio
    async def test_read_history_without_client_logs_debug(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        with patch("app.bots.seller_client.logger.debug") as mock_debug:
            await client.read_history(user_id=123)
        mock_debug.assert_called()

    @pytest.mark.asyncio
    async def test_read_history_uses_chat_id(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        client._client.read_chat_history = AsyncMock()

        await client.read_history(user_id=123)

        client._client.read_chat_history.assert_awaited_once_with(chat_id=123)

    @pytest.mark.asyncio
    async def test_read_history_logs_reconnect_errors(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        with patch.object(
            client, "_with_reconnect", new=AsyncMock(side_effect=RuntimeError("bad"))
        ):
            with patch("app.bots.seller_client.logger.warning") as mock_warning:
                await client.read_history(user_id=123)
        mock_warning.assert_called()

    @pytest.mark.asyncio
    async def test_get_me_returns_none_when_no_client(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        assert await client.get_me() is None

    @pytest.mark.asyncio
    async def test_get_me_returns_current_user(self):
        user = MagicMock(id=1)
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        client._client.get_me = AsyncMock(return_value=user)

        assert await client.get_me() is user

    @pytest.mark.asyncio
    async def test_get_me_returns_none_on_client_error(self):
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        client._client.get_me = AsyncMock(side_effect=RuntimeError("bad session"))

        assert await client.get_me() is None

    def test_on_message_registers_pyrogram_message_handler(self):
        callback = MagicMock()
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()

        with patch("app.bots.seller_client._PYROGRAM_AVAILABLE", True):
            client.on_message(callback)

        client._client.add_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_reraises_flood_and_peer_flood(self, monkeypatch):
        class FakeFloodWait(Exception):
            pass

        class FakePeerFlood(Exception):
            pass

        monkeypatch.setattr("app.bots.seller_client.FloodWait", FakeFloodWait)
        monkeypatch.setattr("app.bots.seller_client.PeerFlood", FakePeerFlood)
        client = SellerClient(account_id="acc1", session_string="sess1")
        client._client = MagicMock()
        client._client.send_message = AsyncMock(side_effect=FakeFloodWait("wait"))

        with pytest.raises(FakeFloodWait):
            await client.send_message(123, "hello")

        client._client.send_message = AsyncMock(side_effect=FakePeerFlood("peer"))
        with pytest.raises(FakePeerFlood):
            await client.send_message(123, "hello")


class TestClientPool:
    def test_register_and_get_client(self):
        pool = ClientPool()
        client = SellerClient(account_id="acc1", session_string="sess1")
        pool.register(client)
        assert pool.get_client("acc1") is client

    def test_get_client_returns_none_when_missing(self):
        pool = ClientPool()
        assert pool.get_client("missing") is None

    def test_unregister_returns_removed_client(self):
        pool = ClientPool()
        client = SellerClient(account_id="acc1", session_string="sess1")
        pool.register(client)

        assert pool.unregister("acc1") is client
        assert pool.unregister("acc1") is None

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

    @pytest.mark.asyncio
    async def test_stop_all_returns_when_empty(self):
        pool = ClientPool()
        await pool.stop_all()


def test_import_sets_event_loop_when_missing():
    loop = asyncio.new_event_loop()
    try:
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            with patch("asyncio.new_event_loop", return_value=loop) as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    importlib.reload(seller_client_module)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(loop)
    finally:
        importlib.reload(seller_client_module)
        loop.close()
