"""Stub Telegram user client (MTProto) for seller accounts.

Intended to be swapped for a real Pyrogram implementation post-MVP.
"""

import asyncio
import logging
import time
from typing import Any

from app.core.humanizer import calculate_typing_delay, calculate_thinking_delay

logger = logging.getLogger(__name__)


def typing_delay_for(text: str, chars_per_min: tuple[float, float] = (200, 350)) -> int:
    """Return simulated typing delay for *text* in milliseconds."""
    return calculate_typing_delay(text, chars_per_min=chars_per_min)


def thinking_delay(min_sec: int = 3, max_sec: int = 15) -> int:
    """Return a random thinking delay in milliseconds."""
    return calculate_thinking_delay(min_sec=min_sec, max_sec=max_sec)


class SellerClient:
    """Placeholder MTProto client for a single Telegram user account."""

    def __init__(self, account_id: str, session_string: str, proxy_url: str | None = None) -> None:
        self.account_id = account_id
        self.session_string = session_string
        self.proxy_url = proxy_url
        self._started = False

    async def start(self) -> None:
        """Initialise the client session."""
        self._started = True
        logger.info("SellerClient %s: starting (proxy=%s)", self.account_id, self.proxy_url)

    async def stop(self) -> None:
        """Terminate the client session."""
        self._started = False
        logger.info("SellerClient %s: stopping", self.account_id)

    async def send_message(self, user_id: int, text: str, typing_delay_ms: int = 0) -> dict[str, Any]:
        """Simulate sending *text* to *user_id*.

        Waits for *typing_delay_ms* if > 0, then returns a mock message dict.
        """
        if typing_delay_ms > 0:
            logger.debug(
                "SellerClient %s: typing delay %d ms for user %s",
                self.account_id,
                typing_delay_ms,
                user_id,
            )
            await asyncio.sleep(typing_delay_ms / 1000.0)

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
        """Stub: notify that the account is typing in a chat."""
        logger.debug("SellerClient %s: set_typing for user %s", self.account_id, user_id)

    async def set_online(self) -> None:
        """Stub: set the account status to online."""
        logger.debug("SellerClient %s: set_online", self.account_id)

    async def read_history(self, user_id: int) -> None:
        """Stub: mark messages in the chat as read."""
        logger.debug("SellerClient %s: read_history for user %s", self.account_id, user_id)


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
