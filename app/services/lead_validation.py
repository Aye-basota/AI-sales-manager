"""Telegram username validation via Pyrogram."""

import logging
from typing import Any, List

from app.config import get_settings

logger = logging.getLogger(__name__)

try:
    from pyrogram import Client
    from pyrogram.types import User

    _PYROGRAM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYROGRAM_AVAILABLE = False


async def validate_telegram_usernames(
    usernames: List[str],
    client: Any | None = None,
) -> List[str]:
    """Validate a list of Telegram usernames and return only valid ones.

    A username is considered valid if the user exists and is not deleted.
    The function also enriches the returned list with ``telegram_user_id``
    where possible (returned as a side-effect dict is not practical, so
    callers that need IDs should use :func:`validate_and_enrich`).

    Args:
        usernames: List of Telegram usernames (without @).
        client: Optional Pyrogram client to reuse.

    Returns:
        List of valid usernames.
    """
    if not _PYROGRAM_AVAILABLE or not usernames:
        return []

    temp_client = False
    if client is None:
        settings = get_settings()
        if settings.telegram_api_id and settings.telegram_api_hash:
            client = Client(
                name="validator",
                api_id=settings.telegram_api_id,
                api_hash=settings.telegram_api_hash,
                in_memory=True,
            )
            temp_client = True
            await client.start()

    if client is None:
        logger.warning("No Telegram client available for username validation")
        return []

    valid: List[str] = []
    # Process in batches of 200 (Pyrogram get_users limit)
    batch_size = 200

    try:
        for i in range(0, len(usernames), batch_size):
            batch = usernames[i : i + batch_size]
            try:
                users = await client.get_users(batch)
                for user in users:
                    if getattr(user, "is_deleted", False):
                        continue
                    username = getattr(user, "username", None)
                    if username:
                        valid.append(username)
            except Exception as exc:
                logger.warning("Validation batch failed: %s", exc)
    except Exception as exc:
        logger.warning("Username validation failed: %s", exc)
    finally:
        if temp_client:
            try:
                await client.stop()
            except Exception:
                pass

    return valid


async def validate_and_enrich(
    usernames: List[str],
    client: Any | None = None,
) -> dict[str, dict[str, Any]]:
    """Validate usernames and return a mapping username -> user info.

    Returns:
        Dictionary mapping valid username to a dict with ``user_id``,
        ``first_name``, ``last_name``.
    """
    if not _PYROGRAM_AVAILABLE or not usernames:
        return {}

    temp_client = False
    if client is None:
        settings = get_settings()
        if settings.telegram_api_id and settings.telegram_api_hash:
            client = Client(
                name="validator_enricher",
                api_id=settings.telegram_api_id,
                api_hash=settings.telegram_api_hash,
                in_memory=True,
            )
            temp_client = True
            await client.start()

    if client is None:
        return {}

    result: dict[str, dict[str, Any]] = {}
    batch_size = 200

    try:
        for i in range(0, len(usernames), batch_size):
            batch = usernames[i : i + batch_size]
            try:
                users = await client.get_users(batch)
                for user in users:
                    if getattr(user, "is_deleted", False):
                        continue
                    username = getattr(user, "username", None)
                    if username:
                        result[username] = {
                            "user_id": getattr(user, "id", None),
                            "first_name": getattr(user, "first_name", None),
                            "last_name": getattr(user, "last_name", None),
                        }
            except Exception as exc:
                logger.warning("Validation batch failed: %s", exc)
    except Exception as exc:
        logger.warning("Validation failed: %s", exc)
    finally:
        if temp_client:
            try:
                await client.stop()
            except Exception:
                pass

    return result
