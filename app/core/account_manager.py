"""Simple Telegram account rotation logic."""

from typing import Protocol


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
