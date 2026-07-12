from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from tests.conftest import MockResult
from app.core.account_manager import (
    select_account,
    mark_message_sent,
    reset_daily_counters,
    mark_account_cooldown,
    mark_account_ready,
    select_account_with_db,
)


@dataclass
class FakeAccount:
    status: str
    daily_messages_sent: int = 0


class TestSelectAccount:
    def test_returns_first_eligible_ready_account(self):
        accounts = [
            FakeAccount(status="warming", daily_messages_sent=0),
            FakeAccount(status="ready", daily_messages_sent=10),
            FakeAccount(status="active", daily_messages_sent=5),
        ]
        result = select_account(accounts, daily_limit=50)
        assert result is accounts[1]

    def test_returns_active_account(self):
        accounts = [
            FakeAccount(status="banned", daily_messages_sent=0),
            FakeAccount(status="active", daily_messages_sent=0),
        ]
        result = select_account(accounts)
        assert result is accounts[1]

    def test_skips_account_at_limit(self):
        accounts = [
            FakeAccount(status="ready", daily_messages_sent=50),
            FakeAccount(status="active", daily_messages_sent=49),
        ]
        result = select_account(accounts, daily_limit=50)
        assert result is accounts[1]

    def test_returns_none_when_no_eligible(self):
        accounts = [
            FakeAccount(status="warming", daily_messages_sent=0),
            FakeAccount(status="ready", daily_messages_sent=50),
            FakeAccount(status="banned", daily_messages_sent=0),
        ]
        assert select_account(accounts, daily_limit=50) is None

    def test_empty_list_returns_none(self):
        assert select_account([]) is None

    def test_respects_custom_limit(self):
        accounts = [
            FakeAccount(status="ready", daily_messages_sent=10),
        ]
        assert select_account(accounts, daily_limit=10) is None
        assert select_account(accounts, daily_limit=11) is accounts[0]


class TestMarkMessageSent:
    def test_increments_counter(self):
        account = FakeAccount(status="ready", daily_messages_sent=0)
        mark_message_sent(account)
        assert account.daily_messages_sent == 1

    def test_increments_multiple_times(self):
        account = FakeAccount(status="ready", daily_messages_sent=5)
        mark_message_sent(account)
        mark_message_sent(account)
        assert account.daily_messages_sent == 7


class TestResetDailyCounters:
    def test_resets_all_accounts(self):
        accounts = [
            FakeAccount(status="ready", daily_messages_sent=10),
            FakeAccount(status="active", daily_messages_sent=25),
            FakeAccount(status="warming", daily_messages_sent=3),
        ]
        reset_daily_counters(accounts)
        for acc in accounts:
            assert acc.daily_messages_sent == 0

    def test_empty_list_does_nothing(self):
        reset_daily_counters([])


class TestDatabaseAccountManager:
    @pytest.mark.asyncio
    async def test_select_account_with_db_returns_scalar_result(self):
        account = FakeAccount(status="ready", daily_messages_sent=1)
        session = AsyncMock()
        session.execute.return_value = MockResult([account])

        result = await select_account_with_db(session, daily_limit=10)

        assert result is account
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_account_cooldown_executes_update(self):
        session = AsyncMock()
        await mark_account_cooldown("account-1", session, wait_seconds=60)

        session.execute.assert_awaited_once()
        statement = session.execute.call_args.args[0]
        assert "UPDATE telegram_accounts" in str(statement)

    @pytest.mark.asyncio
    async def test_mark_account_ready_executes_update(self):
        session = AsyncMock()
        await mark_account_ready("account-1", session)

        session.execute.assert_awaited_once()
        statement = session.execute.call_args.args[0]
        assert "UPDATE telegram_accounts" in str(statement)
