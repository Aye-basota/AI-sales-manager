"""Telegram user client (MTProto) for seller accounts using Pyrogram."""

import asyncio
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

from app.core.humanizer import calculate_typing_delay, calculate_thinking_delay

logger = logging.getLogger(__name__)

try:
    from pyrogram import Client
    from pyrogram.raw.functions.account import SendStatusOnline
    from pyrogram.raw.functions.messages import SendChatAction, ReadHistory
    from pyrogram.raw.types import InputPeerUser, SendMessageTypingAction
    from pyrogram.errors import FloodWait, PeerFlood

    _PYROGRAM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYROGRAM_AVAILABLE = False


def typing_delay_for(text: str, chars_per_min: tuple[float, float] = (200, 350)) -> int:
    """Return simulated typing delay for *text* in milliseconds."""
    return calculate_typing_delay(text, chars_per_min=chars_per_min)


def thinking_delay(min_sec: int = 3, max_sec: int = 15) -> int:
    """Return a random thinking delay in milliseconds."""
    return calculate_thinking_delay(min_sec=min_sec, max_sec=max_sec)


def _parse_proxy(proxy_url: str | None) -> dict[str, Any] | None:
    """Parse a proxy URL into a Pyrogram proxy dict."""
    if not proxy_url:
        return None
    parsed = urlparse(proxy_url)
    scheme = parsed.scheme
    if scheme not in ("socks4", "socks5", "http"):
        logger.warning("Unsupported proxy scheme: %s", scheme)
        return None
    proxy: dict[str, Any] = {
        "scheme": scheme,
        "hostname": parsed.hostname,
        "port": parsed.port,
    }
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    return proxy


class SellerClient:
    """MTProto client for a single Telegram user account."""

    def __init__(
        self,
        account_id: str,
        session_string: str,
        proxy_url: str | None = None,
        api_id: int | None = None,
        api_hash: str | None = None,
        no_updates: bool = True,
    ) -> None:
        self.account_id = account_id
        self.session_string = session_string
        self.proxy_url = proxy_url
        self._started = False
        self._client: Any = None
        self._api_id = api_id
        self._api_hash = api_hash
        self.no_updates = no_updates

        # Initialise Fernet for session encryption only when a key is available.
        self._fernet = None
        if _PYROGRAM_AVAILABLE:
            try:
                from cryptography.fernet import Fernet

                key = os.getenv("SESSION_ENCRYPTION_KEY", "")
                if not key:
                    try:
                        from app.config import get_settings

                        key = get_settings().session_encryption_key
                    except Exception:
                        key = ""
                if key:
                    if isinstance(key, str):
                        key = key.encode()
                    self._fernet = Fernet(key)
            except Exception as exc:
                logger.warning("Failed to initialise Fernet: %s", exc)

    def _decrypt_session(self) -> str:
        """Decrypt the session string if a Fernet instance is configured."""
        if not self._fernet or not self.session_string:
            return self.session_string or ""
        try:
            return self._fernet.decrypt(self.session_string.encode()).decode()
        except Exception:
            # If decryption fails, assume the string is plaintext.
            return self.session_string

    def _init_client(self) -> Any:
        """Build a Pyrogram Client from the stored credentials."""
        if not self._api_id or not self._api_hash:
            return None
        session_str = self._decrypt_session()
        proxy = _parse_proxy(self.proxy_url)
        return Client(
            name=f"seller_{self.account_id}",
            api_id=self._api_id,
            api_hash=self._api_hash,
            session_string=session_str,
            proxy=proxy,
            in_memory=True,
            no_updates=self.no_updates,
        )

    async def start(self) -> None:
        """Initialise the client session."""
        if _PYROGRAM_AVAILABLE and self._api_id and self._api_hash:
            self._client = self._init_client()
            if self._client:
                await self._client.start()
        self._started = True
        logger.info("SellerClient %s: started", self.account_id)

    async def stop(self) -> None:
        """Terminate the client session."""
        if self._client is not None:
            try:
                await self._client.stop()
            except Exception as exc:
                logger.warning("SellerClient %s: error stopping client: %s", self.account_id, exc)
            self._client = None
        self._started = False
        logger.info("SellerClient %s: stopped", self.account_id)

    async def send_message(
        self, user_id: int, text: str, typing_delay_ms: int = 0
    ) -> dict[str, Any]:
        """Send *text* to *user_id*.

        Waits for *typing_delay_ms* if > 0, then returns a message dict.
        Raises :class:`pyrogram.errors.FloodWait` or
        :class:`pyrogram.errors.PeerFlood` on Telegram rate limits.
        """
        if typing_delay_ms > 0:
            logger.debug(
                "SellerClient %s: typing delay %d ms for user %s",
                self.account_id,
                typing_delay_ms,
                user_id,
            )
            await asyncio.sleep(typing_delay_ms / 1000.0)

        if self._client is not None:
            try:
                msg = await self._client.send_message(chat_id=user_id, text=text)
                return {
                    "message_id": msg.id,
                    "chat": {
                        "id": getattr(msg.chat, "id", user_id),
                        "type": getattr(msg.chat, "type", "private"),
                    },
                    "date": msg.date,
                    "text": msg.text,
                }
            except FloodWait:
                logger.warning(
                    "SellerClient %s: FloodWait for user %s", self.account_id, user_id
                )
                raise
            except PeerFlood:
                logger.warning(
                    "SellerClient %s: PeerFlood for user %s", self.account_id, user_id
                )
                raise

        # Fallback stub behaviour when no real MTProto client is active.
        mock_msg_id = int(time.time() * 1000)
        logger.info(
            "SellerClient %s: sent message to user %s (msg_id=%s, len=%d)",
            self.account_id,
            user_id,
            mock_msg_id,
            len(text),
        )
        return {
            "message_id": mock_msg_id,
            "chat": {"id": user_id, "type": "private"},
            "date": int(time.time()),
            "text": text,
        }

    async def set_typing(self, user_id: int) -> None:
        """Notify that the account is typing in a chat."""
        if self._client is not None:
            try:
                peer = InputPeerUser(user_id=user_id, access_hash=0)
                await self._client.invoke(
                    SendChatAction(peer=peer, action=SendMessageTypingAction())
                )
            except Exception as exc:
                logger.warning("SellerClient %s: set_typing error %s", self.account_id, exc)
        logger.debug("SellerClient %s: set_typing for user %s", self.account_id, user_id)

    async def set_online(self) -> None:
        """Set the account status to online."""
        if self._client is not None:
            try:
                await self._client.invoke(SendStatusOnline())
            except Exception as exc:
                logger.warning("SellerClient %s: set_online error %s", self.account_id, exc)
        logger.debug("SellerClient %s: set_online", self.account_id)

    async def read_history(self, user_id: int) -> None:
        """Mark messages in the chat as read."""
        if self._client is not None:
            try:
                peer = InputPeerUser(user_id=user_id, access_hash=0)
                await self._client.invoke(ReadHistory(peer=peer, max_id=0))
            except Exception as exc:
                logger.warning("SellerClient %s: read_history error %s", self.account_id, exc)
        logger.debug("SellerClient %s: read_history for user %s", self.account_id, user_id)

    async def get_me(self) -> Any | None:
        """Return the current Telegram user if the session is valid."""
        if self._client is None:
            return None
        try:
            return await self._client.get_me()
        except Exception as exc:
            logger.warning("SellerClient %s: get_me error %s", self.account_id, exc)
            return None

    def on_message(self, callback) -> None:
        """Register a Pyrogram message handler."""
        if _PYROGRAM_AVAILABLE and self._client is not None:
            from pyrogram.handlers import MessageHandler
            self._client.add_handler(MessageHandler(callback))


class ClientPool:
    """Manage multiple :class:`SellerClient` instances."""

    def __init__(self) -> None:
        self._clients: dict[str, SellerClient] = {}

    def register(self, client: SellerClient) -> None:
        """Add a *client* to the pool."""
        self._clients[client.account_id] = client
        logger.debug("ClientPool: registered client %s", client.account_id)

    def unregister(self, account_id: str) -> SellerClient | None:
        """Remove and return a client by *account_id*."""
        client = self._clients.pop(account_id, None)
        if client:
            logger.debug("ClientPool: unregistered client %s", account_id)
        return client

    def get_client(self, account_id: str) -> SellerClient | None:
        """Return the client associated with *account_id*, or ``None``."""
        return self._clients.get(account_id)

    async def start_all(self) -> None:
        """Start every registered client concurrently."""
        if not self._clients:
            logger.warning("ClientPool: start_all called with no clients")
            return
        await asyncio.gather(*(client.start() for client in self._clients.values()))

    async def stop_all(self) -> None:
        """Stop every registered client concurrently."""
        if not self._clients:
            return
        await asyncio.gather(*(client.stop() for client in self._clients.values()))
