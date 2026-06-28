import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.scheduler import (
    should_send_to_contact,
    is_within_working_hours,
    next_contact_to_process,
    process_campaigns,
    send_initial_message,
    send_follow_up_message,
    CampaignScheduler,
)


class TestShouldSendToContact:
    def test_pending_always_ready(self):
        assert should_send_to_contact("pending", None, 24, datetime.now()) is True
        assert (
            should_send_to_contact("pending", datetime.now(), 24, datetime.now())
            is True
        )

    def test_sent_ready_after_delay(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        last_sent = now - timedelta(hours=25)
        assert should_send_to_contact("sent", last_sent, 24, now) is True

    def test_sent_not_ready_before_delay(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        last_sent = now - timedelta(hours=23)
        assert should_send_to_contact("sent", last_sent, 24, now) is False

    def test_follow_up_sent_ready_after_delay(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        last_sent = now - timedelta(hours=48)
        assert should_send_to_contact("follow_up_sent", last_sent, 24, now) is True

    def test_sent_ready_when_no_last_sent(self):
        now = datetime.now()
        assert should_send_to_contact("sent", None, 24, now) is True

    def test_other_status_returns_false(self):
        now = datetime.now()
        assert should_send_to_contact("replied", None, 24, now) is False
        assert should_send_to_contact("closed", None, 24, now) is False


class TestIsWithinWorkingHours:
    def test_within_hours(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        assert (
            is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now)
            is True
        )

    def test_at_start_boundary(self):
        now = datetime(2024, 1, 1, 9, 0, 0)
        assert (
            is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now)
            is True
        )

    def test_at_end_boundary(self):
        now = datetime(2024, 1, 1, 18, 0, 0)
        assert (
            is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now)
            is True
        )

    def test_before_start(self):
        now = datetime(2024, 1, 1, 8, 59, 0)
        assert (
            is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now)
            is False
        )

    def test_after_end(self):
        now = datetime(2024, 1, 1, 18, 1, 0)
        assert (
            is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now)
            is False
        )

    def test_overnight_shift(self):
        now = datetime(2024, 1, 1, 23, 0, 0)
        assert (
            is_within_working_hours("Europe/Moscow", time(22, 0), time(6, 0), now)
            is True
        )


@dataclass
class FakeCampaignContact:
    status: str
    initial_sent_at: datetime | None = None
    follow_up_sent_at: datetime | None = None
    message_count: int = 0


@dataclass
class FakeScript:
    max_messages: int = 2
    follow_up_delay_hours: int = 24
    working_hours_start: time = time(9, 0)
    working_hours_end: time = time(18, 0)
    timezone: str = "Europe/Moscow"


class TestNextContactToProcess:
    def test_no_contacts_returns_empty(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        assert next_contact_to_process([], FakeScript(), now) == []

    def test_outside_working_hours_returns_empty(self):
        now = datetime(2024, 1, 1, 20, 0, 0)
        contacts = [FakeCampaignContact(status="pending")]
        assert next_contact_to_process(contacts, FakeScript(), now) == []

    def test_pending_contact_ready(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [FakeCampaignContact(status="pending")]
        result = next_contact_to_process(contacts, FakeScript(), now)
        assert result == contacts

    def test_sent_contact_ready_after_delay(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [
            FakeCampaignContact(
                status="sent",
                initial_sent_at=now - timedelta(hours=25),
                message_count=1,
            )
        ]
        result = next_contact_to_process(contacts, FakeScript(), now)
        assert result == contacts

    def test_sent_contact_not_ready_before_delay(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [
            FakeCampaignContact(
                status="sent",
                initial_sent_at=now - timedelta(hours=23),
                message_count=1,
            )
        ]
        result = next_contact_to_process(contacts, FakeScript(), now)
        assert result == []

    def test_max_messages_exceeded(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [
            FakeCampaignContact(
                status="sent",
                initial_sent_at=now - timedelta(hours=25),
                message_count=2,
            )
        ]
        result = next_contact_to_process(contacts, FakeScript(max_messages=2), now)
        assert result == []

    def test_mixed_contacts_filters_correctly(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [
            FakeCampaignContact(status="pending"),
            FakeCampaignContact(
                status="sent",
                initial_sent_at=now - timedelta(hours=23),
                message_count=1,
            ),
            FakeCampaignContact(
                status="sent",
                initial_sent_at=now - timedelta(hours=25),
                message_count=1,
            ),
            FakeCampaignContact(
                status="sent",
                initial_sent_at=now - timedelta(hours=25),
                message_count=2,
            ),
        ]
        result = next_contact_to_process(contacts, FakeScript(), now)
        assert result == [contacts[0], contacts[2]]

    def test_follow_up_sent_ready_after_delay(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [
            FakeCampaignContact(
                status="follow_up_sent",
                initial_sent_at=now - timedelta(hours=48),
                follow_up_sent_at=now - timedelta(hours=25),
                message_count=2,
            )
        ]
        result = next_contact_to_process(contacts, FakeScript(max_messages=3), now)
        assert result == contacts

    def test_initial_sent_at_none_treated_as_ready(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [
            FakeCampaignContact(status="sent", initial_sent_at=None, message_count=1)
        ]
        result = next_contact_to_process(contacts, FakeScript(), now)
        assert result == contacts


# Simple mock helpers for async DB tests
class _SimpleMockScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


class _SimpleMockResult:
    def __init__(self, items=None, scalar_value=None):
        self._items = items or []
        self._scalar_value = scalar_value

    def scalars(self):
        return _SimpleMockScalarResult(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalar(self):
        return self._scalar_value

    def all(self):
        return self._items


@dataclass
class MockTelegramAccount:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: str = "ready"
    daily_messages_sent: int = 0
    last_message_at: datetime | None = None
    session_string: str | None = "test_session"
    proxy_url: str | None = None


@pytest.mark.asyncio
class TestProcessCampaigns:
    async def test_no_running_campaigns(self, mock_db):
        mock_db.execute.return_value = _SimpleMockResult([])
        await process_campaigns(mock_db)
        assert mock_db.commit.called is False

    async def test_campaign_outside_working_hours(
        self, mock_db, sample_campaign, sample_script
    ):
        sample_campaign.status = "running"
        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),  # campaigns
            _SimpleMockResult([sample_script]),  # script
        ]
        with patch("app.core.scheduler.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 20, 0, 0)
            await process_campaigns(mock_db)
        assert mock_db.execute.call_count == 2

    async def test_ready_contact_initial_sent(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        sample_contact.telegram_user_id = 123456

        account = MockTelegramAccount()

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),  # campaigns
            _SimpleMockResult([sample_script]),  # script
            _SimpleMockResult([cc]),  # campaign contacts
            _SimpleMockResult([sample_contact]),  # contact
            _SimpleMockResult([]),  # conversation (not found)
            _SimpleMockResult([account]),  # accounts
        ]

        with patch(
            "app.core.scheduler.send_initial_message", new_callable=AsyncMock
        ) as mock_send:
            await process_campaigns(mock_db)
            mock_send.assert_awaited_once()
            assert mock_db.commit.called is True

    async def test_rate_limited_account_skips(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        sample_contact.telegram_user_id = 123456

        account = MockTelegramAccount(last_message_at=datetime.now())

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([]),
            _SimpleMockResult([account]),
        ]

        with patch(
            "app.core.scheduler.send_initial_message", new_callable=AsyncMock
        ) as mock_send:
            await process_campaigns(mock_db)
            mock_send.assert_not_awaited()

    async def test_contact_without_telegram_user_id_skipped(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        sample_contact.telegram_user_id = None

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
        ]

        with patch(
            "app.core.scheduler.send_initial_message", new_callable=AsyncMock
        ) as mock_send:
            await process_campaigns(mock_db)
            mock_send.assert_not_awaited()

    async def test_processed_contacts_counts_unique_contacts(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_campaign.processed_contacts = 0
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="initial_sent",
            message_count=1,
            initial_sent_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )
        sample_contact.telegram_user_id = 123456

        account = MockTelegramAccount()

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([]),
            _SimpleMockResult([account]),
        ]

        with patch("app.core.scheduler.send_follow_up_message", new_callable=AsyncMock):
            await process_campaigns(mock_db)

        # Follow-up should not increment processed_contacts.
        assert sample_campaign.processed_contacts == 0

    async def test_assigned_account_ineligible_falls_back(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact
        from app.models.telegram_account import TelegramAccount

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        sample_contact.telegram_user_id = 123456

        assigned_account = TelegramAccount(
            id=uuid.uuid4(),
            phone="+111",
            status="cooldown",
            session_string="sess",
        )
        sample_contact.assigned_account_id = assigned_account.id

        fallback_account = MockTelegramAccount()

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([]),
            _SimpleMockResult([assigned_account]),  # assigned account lookup
            _SimpleMockResult([fallback_account]),  # fallback pool
        ]

        with patch(
            "app.core.scheduler.send_initial_message", new_callable=AsyncMock
        ) as mock_send:
            await process_campaigns(mock_db)
            mock_send.assert_awaited_once()


@pytest.mark.asyncio
class TestSendInitialMessage:
    async def test_successful_send(self, mock_db):
        from app.models.campaign import CampaignContact
        from app.models.contact import Contact
        from app.models.conversation import Conversation
        from app.models.script import Script
        from app.models.telegram_account import TelegramAccount

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            status="pending",
            message_count=0,
        )
        contact = Contact(
            id=cc.contact_id,
            telegram_user_id=123456,
            first_name="John",
            city="New York",
        )
        conversation = Conversation(
            id=uuid.uuid4(),
            contact_id=contact.id,
            campaign_id=cc.campaign_id,
            current_state="cold",
        )
        script = Script(
            id=uuid.uuid4(),
            name="Test",
            role_prompt="Sales",
            goal="Book",
            max_messages=3,
            follow_up_delay_hours=24,
            working_hours_start=time(9, 0),
            working_hours_end=time(18, 0),
            timezone="Europe/Moscow",
        )
        account = TelegramAccount(
            id=uuid.uuid4(),
            phone="+123",
            status="ready",
            daily_messages_sent=0,
            session_string="sess",
        )

        mock_llm_response = {"text": "Hello!", "model": "gpt-4", "tokens_used": 10}

        with patch("app.llm.engine.LLMEngine") as MockEngine:
            engine_inst = MockEngine.return_value
            engine_inst.generate_response_with_guardrails = AsyncMock(
                return_value=mock_llm_response
            )

            with patch("app.bots.seller_client.SellerClient") as MockClient:
                client_inst = MockClient.return_value
                client_inst.start = AsyncMock()
                client_inst.send_message = AsyncMock(return_value={"message_id": 1})
                client_inst.stop = AsyncMock()

                await send_initial_message(
                    db_session=mock_db,
                    campaign_contact=cc,
                    contact=contact,
                    conversation=conversation,
                    script=script,
                    account=account,
                )

                assert cc.status == "initial_sent"
                assert cc.message_count == 1
                assert account.daily_messages_sent == 1
                assert conversation.current_state == "warm"
                mock_db.add.assert_called()
                client_inst.start.assert_awaited_once()
                client_inst.send_message.assert_awaited_once()
                client_inst.stop.assert_awaited_once()

    async def test_guardrails_block_message(self, mock_db):
        from app.models.campaign import CampaignContact
        from app.models.contact import Contact
        from app.models.conversation import Conversation
        from app.models.script import Script
        from app.models.telegram_account import TelegramAccount

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            status="pending",
            message_count=0,
        )
        contact = Contact(id=cc.contact_id, telegram_user_id=123456)
        conversation = Conversation(
            id=uuid.uuid4(),
            contact_id=contact.id,
            campaign_id=cc.campaign_id,
            current_state="cold",
        )
        script = Script(id=uuid.uuid4(), name="Test", role_prompt="Sales", goal="Book")
        account = TelegramAccount(
            id=uuid.uuid4(),
            phone="+123",
            status="ready",
            daily_messages_sent=0,
            session_string="sess",
        )

        mock_llm_response = {"text": "", "model": "fallback", "tokens_used": 0}

        with patch("app.llm.engine.LLMEngine") as MockEngine:
            engine_inst = MockEngine.return_value
            engine_inst.generate_response_with_guardrails = AsyncMock(
                return_value=mock_llm_response
            )

            with pytest.raises(RuntimeError, match="LLM returned empty text"):
                await send_initial_message(
                    db_session=mock_db,
                    campaign_contact=cc,
                    contact=contact,
                    conversation=conversation,
                    script=script,
                    account=account,
                )


@pytest.mark.asyncio
class TestSendFollowUpMessage:
    async def test_successful_send(self, mock_db):
        from app.models.campaign import CampaignContact
        from app.models.contact import Contact
        from app.models.conversation import Conversation
        from app.models.script import Script
        from app.models.telegram_account import TelegramAccount

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            status="initial_sent",
            message_count=1,
            initial_sent_at=datetime.now() - timedelta(hours=25),
        )
        contact = Contact(id=cc.contact_id, telegram_user_id=123456, first_name="John")
        conversation = Conversation(
            id=uuid.uuid4(),
            contact_id=contact.id,
            campaign_id=cc.campaign_id,
            current_state="warm",
        )
        script = Script(
            id=uuid.uuid4(),
            name="Test",
            role_prompt="Sales",
            goal="Book",
            max_messages=3,
            follow_up_delay_hours=24,
        )
        account = TelegramAccount(
            id=uuid.uuid4(),
            phone="+123",
            status="ready",
            daily_messages_sent=0,
            session_string="sess",
        )

        mock_llm_response = {"text": "Follow up!", "model": "gpt-4", "tokens_used": 5}

        with patch("app.llm.engine.LLMEngine") as MockEngine:
            engine_inst = MockEngine.return_value
            engine_inst.generate_response_with_guardrails = AsyncMock(
                return_value=mock_llm_response
            )

            with patch(
                "app.services.conversation_service.get_conversation_context",
                new_callable=AsyncMock,
            ) as mock_ctx:
                mock_ctx.return_value = {"messages": [], "facts": {}}

                with patch("app.bots.seller_client.SellerClient") as MockClient:
                    client_inst = MockClient.return_value
                    client_inst.start = AsyncMock()
                    client_inst.send_message = AsyncMock(return_value={"message_id": 2})
                    client_inst.stop = AsyncMock()

                    await send_follow_up_message(
                        db_session=mock_db,
                        campaign_contact=cc,
                        contact=contact,
                        conversation=conversation,
                        script=script,
                        account=account,
                    )

                    assert cc.status == "follow_up_sent"
                    assert cc.message_count == 2
                    assert account.daily_messages_sent == 1
                    assert conversation.current_state == "follow_up"
                    mock_db.add.assert_called()
                    client_inst.send_message.assert_awaited_once()


class TestCampaignScheduler:
    def test_start_shutdown(self):
        sched = CampaignScheduler()
        with patch.object(sched._scheduler, "start") as mock_start:
            with patch.object(sched._scheduler, "add_job") as mock_add_job:
                sched.start()
                assert mock_add_job.call_count == 4
                mock_start.assert_called_once()

        with patch.object(sched._scheduler, "shutdown") as mock_shutdown:
            sched.shutdown()
            mock_shutdown.assert_called_once()

    def test_is_running(self):
        sched = CampaignScheduler()
        with patch.object(type(sched._scheduler), "running", new=True):
            assert sched.is_running() is True
        with patch.object(type(sched._scheduler), "running", new=False):
            assert sched.is_running() is False

    @pytest.mark.asyncio
    async def test_run_process_campaigns(self):
        sched = CampaignScheduler()
        with patch(
            "app.core.scheduler.process_campaigns", new_callable=AsyncMock
        ) as mock_process:
            with patch("app.db.session.AsyncSessionLocal") as MockSession:
                session_inst = AsyncMock()
                MockSession.return_value.__aenter__ = AsyncMock(
                    return_value=session_inst
                )
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                await sched._run_process_campaigns()
                mock_process.assert_awaited_once()
