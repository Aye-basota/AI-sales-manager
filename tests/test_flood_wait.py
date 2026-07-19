"""Tests for FloodWait / PeerFlood handling in the scheduler."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.scheduler import (
    AccountFloodError,
    AccountPeerFloodError,
    send_initial_message,
)


class MockFloodWait(Exception):
    def __init__(self, value: int = 120):
        self.value = value
        super().__init__(f"A wait of {value} seconds is required")


class MockPeerFlood(Exception):
    pass


@pytest.fixture
def sample_entities():
    campaign_contact = MagicMock()
    campaign_contact.status = "pending"
    campaign_contact.message_count = 0

    contact = MagicMock()
    contact.telegram_user_id = 123456

    conversation = MagicMock()
    conversation.current_state = "cold"

    script = MagicMock()
    script.goal = "Book a meeting"
    script.role_prompt = "Sales"

    account = MagicMock()
    account.id = uuid4()
    account.session_string = "sess"
    account.proxy_url = None
    account.daily_messages_sent = 0

    return campaign_contact, contact, conversation, script, account


@pytest.mark.asyncio
async def test_send_initial_message_raises_account_flood_error(sample_entities):
    cc, contact, conv, script, account = sample_entities

    with patch("app.core.scheduler.FloodWait", MockFloodWait):
        with patch("app.core.scheduler._PYROGRAM_ERRORS_AVAILABLE", True):
            with patch("app.llm.engine.LLMEngine") as MockEngine:
                MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                    return_value={"text": "Hi", "model": "gpt-4", "tokens_used": 1}
                )

                with patch("app.bots.seller_client.SellerClient") as MockClient:
                    client_inst = MockClient.return_value
                    client_inst.start = AsyncMock()
                    client_inst.stop = AsyncMock()
                    client_inst.send_message = AsyncMock(side_effect=MockFloodWait(120))

                    with pytest.raises(AccountFloodError) as exc_info:
                        await send_initial_message(
                            db_session=MagicMock(),
                            campaign_contact=cc,
                            contact=contact,
                            conversation=conv,
                            script=script,
                            account=account,
                        )
                    assert exc_info.value.wait_seconds == 120


@pytest.mark.asyncio
async def test_send_initial_message_raises_peer_flood_error(sample_entities):
    cc, contact, conv, script, account = sample_entities

    with patch("app.core.scheduler.PeerFlood", MockPeerFlood):
        with patch("app.core.scheduler._PYROGRAM_ERRORS_AVAILABLE", True):
            with patch("app.llm.engine.LLMEngine") as MockEngine:
                MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                    return_value={"text": "Hi", "model": "gpt-4", "tokens_used": 1}
                )

                with patch("app.bots.seller_client.SellerClient") as MockClient:
                    client_inst = MockClient.return_value
                    client_inst.start = AsyncMock()
                    client_inst.stop = AsyncMock()
                    client_inst.send_message = AsyncMock(side_effect=MockPeerFlood())

                    with pytest.raises(AccountPeerFloodError):
                        await send_initial_message(
                            db_session=MagicMock(),
                            campaign_contact=cc,
                            contact=contact,
                            conversation=conv,
                            script=script,
                            account=account,
                        )


def _make_result(items=None, single=None):
    class Scalars:
        def all(self):
            return items or []

        def first(self):
            records = items or []
            return records[0] if records else None

    class Result:
        def scalars(self, *args, **kwargs):
            return Scalars()

        def scalar_one_or_none(self):
            return single

    return Result()


@pytest.mark.asyncio
async def test_process_campaigns_retries_on_flood_wait():
    from app.core.scheduler import process_campaigns
    from app.models.campaign import Campaign, CampaignContact
    from app.models.script import Script
    from app.models.contact import Contact
    from app.models.telegram_account import TelegramAccount

    script_id = uuid4()
    campaign_id = uuid4()
    contact_id = uuid4()
    account1_id = uuid4()
    account2_id = uuid4()

    campaign = Campaign(id=campaign_id, script_id=script_id, status="running")
    script = Script(
        id=script_id,
        name="Test",
        role_prompt="Sales",
        goal="Book",
        max_messages=3,
        follow_up_delay_hours=24,
        working_hours_start=datetime.strptime("00:00", "%H:%M").time(),
        working_hours_end=datetime.strptime("23:59", "%H:%M").time(),
        timezone="Europe/Moscow",
    )
    contact = Contact(
        id=contact_id,
        telegram_user_id=111,
        first_name="John",
        assigned_account_id=None,
    )
    cc = CampaignContact(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact_id,
        status="pending",
        message_count=0,
    )
    account1 = TelegramAccount(
        id=account1_id,
        phone="+1",
        status="ready",
        daily_messages_sent=0,
        session_string="s1",
    )
    account2 = TelegramAccount(
        id=account2_id,
        phone="+2",
        status="ready",
        daily_messages_sent=0,
        session_string="s2",
    )

    mock_db = MagicMock()
    calls = [
        _make_result([campaign]),
        _make_result(single=script),
        _make_result([cc]),
        _make_result(single=contact),
        _make_result(single=None),
        _make_result([account1, account2]),
        _make_result([]),
        _make_result([account2]),
    ]
    mock_db.execute = AsyncMock(side_effect=calls)
    mock_db.commit = AsyncMock()

    send_calls = []

    async def fake_send_initial(*args, **kwargs):
        account = kwargs.get("account")
        if account.id == account1_id and len(send_calls) == 0:
            send_calls.append(account1_id)
            raise AccountFloodError(account1_id, wait_seconds=120)
        send_calls.append(account.id)

    with patch(
        "app.core.scheduler.send_initial_message", side_effect=fake_send_initial
    ):
        with patch(
            "app.core.account_manager.mark_account_cooldown", new_callable=AsyncMock
        ) as mock_cooldown:
            await process_campaigns(mock_db)

    # First account should be marked cooldown
    mock_cooldown.assert_awaited_once()
    args, kwargs = mock_cooldown.call_args
    assert args[0] == account1_id
    assert kwargs.get("wait_seconds") == 120

    # send_initial_message should be called twice (first fails, retry succeeds)
    assert len(send_calls) == 2
    assert send_calls[0] == account1_id
    assert send_calls[1] == account2_id
