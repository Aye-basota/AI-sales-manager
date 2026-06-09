"""Simple Telegram account rotation logic."""

from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_account import TelegramAccount


class _HasAccountAttrs(Protocol):
    status: str
    daily_messages_sent: int


def select_account(
    accounts: list[_HasAccountAttrs],
    daily_limit: int = 50,
) -> _HasAccountAttrs | None:
    """Return the first eligible account or None.

    Eligible accounts have status ``ready`` or ``active`` and have sent
    fewer than *daily_limit* messages today.
    """
    for account in accounts:
        if account.status in ("ready", "active") and account.daily_messages_sent < daily_limit:
            return account
    return None


def mark_message_sent(account: _HasAccountAttrs) -> None:
    """Increment the account's daily message counter."""
    account.daily_messages_sent += 1


def reset_daily_counters(accounts: list[_HasAccountAttrs]) -> None:
    """Reset ``daily_messages_sent`` to 0 for all accounts."""
    for account in accounts:
        account.daily_messages_sent = 0


async def select_account_with_db(
    session: AsyncSession, daily_limit: int = 50
) -> TelegramAccount | None:
    """Return the first eligible account from the database or ``None``."""
    result = await session.execute(
        select(TelegramAccount).where(
            TelegramAccount.status.in_(["ready", "active"]),
            TelegramAccount.daily_messages_sent < daily_limit,
        )
    )
    return result.scalar_one_or_none()


async def mark_account_cooldown(
    account_id, session: AsyncSession, wait_seconds: int = 24 * 3600
) -> None:
    """Mark account as ``cooldown`` for the specified duration."""
    await session.execute(
        update(TelegramAccount)
        .where(TelegramAccount.id == account_id)
        .values(
            status="cooldown",
            cooldown_until=datetime.utcnow() + timedelta(seconds=wait_seconds),
        )
    )
    await session.commit()


async def mark_account_ready(account_id, session: AsyncSession) -> None:
    """Mark account as ``ready`` and clear cooldown/error state."""
    await session.execute(
        update(TelegramAccount)
        .where(TelegramAccount.id == account_id)
        .values(
            status="ready",
            cooldown_until=None,
            last_error=None,
        )
    )
    await session.commit()


async def reset_daily_counters_db(session: AsyncSession) -> None:
    """Reset ``daily_messages_sent`` to ``0`` for all accounts in the database."""
    await session.execute(
        update(TelegramAccount).values(daily_messages_sent=0)
    )
    await session.commit()


async def recover_cooldown_accounts(session: AsyncSession, hours: int = 24) -> None:
    """Recover accounts from ``cooldown`` to ``ready`` if enough time has passed."""
    threshold = datetime.utcnow() - timedelta(hours=hours)
    await session.execute(
        update(TelegramAccount)
        .where(
            TelegramAccount.status == "cooldown",
            TelegramAccount.cooldown_until <= threshold,
        )
        .values(
            status="ready",
            cooldown_until=None,
            last_error=None,
        )
    )
    await session.commit()
