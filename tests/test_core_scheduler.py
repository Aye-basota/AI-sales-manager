import uuid
import importlib
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.scheduler as scheduler_module
from app.core.scheduler import (
    AccountFloodError,
    AccountPeerFloodError,
    ContactPeerInvalidError,
    should_send_to_contact,
    is_within_working_hours,
    next_contact_to_process,
    process_campaigns,
    send_initial_message,
    send_follow_up_message,
    CampaignScheduler,
    _campaign_contact_queue_key,
    _contact_chat_id,
    _contact_chat_candidates,
    _contact_has_chat_id,
    _increment_processed_contacts,
    _is_eligible_account,
    _should_send_follow_up,
    _get_sync_db_url,
    normalize_timezone,
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

    def test_follow_up_sent_waits_for_auto_close(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        last_sent = now - timedelta(hours=48)
        assert should_send_to_contact("follow_up_sent", last_sent, 24, now) is False

    def test_sent_ready_when_no_last_sent(self):
        now = datetime.now()
        assert should_send_to_contact("sent", None, 24, now) is True

    def test_other_status_returns_false(self):
        now = datetime.now()
        assert should_send_to_contact("replied", None, 24, now) is False
        assert should_send_to_contact("closed", None, 24, now) is False


class TestSchedulerHelpers:
    def test_contact_chat_id_prefers_username_and_detects_any_address(self):
        contact = MagicMock(telegram_username="@leaduser", telegram_user_id=123)
        assert _contact_chat_id(contact) == "leaduser"
        assert _contact_chat_candidates(contact) == ["leaduser", 123]
        assert _contact_has_chat_id(contact) is True

        contact.telegram_username = ""
        assert _contact_chat_id(contact) == 123
        assert _contact_chat_candidates(contact) == [123]
        assert _contact_has_chat_id(contact) is True

        contact.telegram_user_id = None
        assert _contact_has_chat_id(contact) is False

    def test_queue_key_handles_naive_datetimes_and_missing_position(self):
        cc = FakeCampaignContact(
            status="pending",
            initial_sent_at=datetime(2024, 1, 1, 12, 0),
        )
        cc.queue_position = None
        cc.contact_id = uuid.UUID(int=2)

        key = _campaign_contact_queue_key(cc)

        assert key[0] is False
        assert key[1] is True
        assert key[-1] == str(uuid.UUID(int=2))

    def test_eligible_account_rejects_bad_status_missing_session_and_cooldown(self):
        now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        account = MockTelegramAccount(status="cooldown")
        assert _is_eligible_account(account, now) is False

        account.status = "ready"
        account.session_string = ""
        assert _is_eligible_account(account, now) is False

        account.session_string = "session"
        account.cooldown_until = datetime(2024, 1, 1, 1, 0)
        assert _is_eligible_account(account, now) is False

        account.cooldown_until = datetime(2023, 12, 31, tzinfo=timezone.utc)
        assert _is_eligible_account(account, now) is True

    def test_normalize_timezone_defaults_aliases_and_empty_values(self):
        assert normalize_timezone(None) == "Europe/Moscow"
        assert normalize_timezone("  ") == "Europe/Moscow"
        assert normalize_timezone("msk") == "Europe/Moscow"
        assert normalize_timezone("UTC") == "UTC"

    def test_should_send_follow_up_requires_clean_no_reply_context(self):
        cc = SimpleNamespace(
            status="initial_sent",
            reply_received_at=None,
            follow_up_sent_at=None,
        )
        conversation = SimpleNamespace(
            current_state="warm",
            operator_status=None,
            was_escalated=False,
        )

        assert _should_send_follow_up(cc, conversation) is True

        cc.reply_received_at = datetime.now(timezone.utc)
        assert _should_send_follow_up(cc, conversation) is False
        cc.reply_received_at = None

        cc.follow_up_sent_at = datetime.now(timezone.utc)
        assert _should_send_follow_up(cc, conversation) is False
        cc.follow_up_sent_at = None

        conversation.current_state = "closed"
        assert _should_send_follow_up(cc, conversation) is False
        conversation.current_state = "warm"

        conversation.operator_status = "qualified"
        assert _should_send_follow_up(cc, conversation) is False
        conversation.operator_status = None

        conversation.was_escalated = True
        assert _should_send_follow_up(cc, conversation) is False


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

    def test_invalid_timezone_falls_back_to_utc(self):
        now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert is_within_working_hours("bad/timezone", time(9, 0), time(18, 0), now)


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

    def test_follow_up_sent_waits_for_auto_close(self):
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
        assert result == []

    def test_initial_sent_at_none_treated_as_ready(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        contacts = [
            FakeCampaignContact(status="sent", initial_sent_at=None, message_count=1)
        ]
        result = next_contact_to_process(contacts, FakeScript(), now)
        assert result == contacts


class TestCampaignContactQueueKey:
    def test_orders_pending_contacts_before_followups_then_by_queue_position(self):
        now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        first_pending = FakeCampaignContact(status="pending")
        first_pending.queue_position = 1
        second_pending = FakeCampaignContact(status="pending")
        second_pending.queue_position = 2
        first_already_sent = FakeCampaignContact(
            status="initial_sent",
            initial_sent_at=now - timedelta(hours=25),
            message_count=1,
        )
        first_already_sent.queue_position = 1

        ordered = sorted(
            [second_pending, first_already_sent, first_pending],
            key=_campaign_contact_queue_key,
        )

        assert ordered == [first_pending, second_pending, first_already_sent]


@pytest.mark.asyncio
async def test_increment_processed_contacts_updates_expired_campaign_via_sql():
    campaign = MagicMock(id=uuid.uuid4(), processed_contacts=4)
    db = AsyncMock()

    with patch("app.core.scheduler.sa_inspect", return_value=MagicMock(expired=True)):
        await _increment_processed_contacts(db, campaign.id, campaign)

    db.execute.assert_awaited_once()
    assert campaign.processed_contacts == 4


@pytest.mark.asyncio
async def test_increment_processed_contacts_handles_non_inspectable_campaign():
    campaign = MagicMock(processed_contacts=4)
    db = AsyncMock()

    with patch("app.core.scheduler.sa_inspect", side_effect=scheduler_module.NoInspectionAvailable()):
        await _increment_processed_contacts(db, uuid.uuid4(), campaign)

    assert campaign.processed_contacts == 5


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


def _build_send_objects(status: str = "pending"):
    from app.models.campaign import CampaignContact
    from app.models.contact import Contact
    from app.models.conversation import Conversation
    from app.models.script import Script
    from app.models.telegram_account import TelegramAccount

    campaign_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        contact_id=contact_id,
        status=status,
        message_count=0 if status == "pending" else 1,
        initial_sent_at=datetime.now(timezone.utc) - timedelta(hours=25),
    )
    contact = Contact(
        id=contact_id,
        telegram_user_id=123456,
        telegram_username="leaduser",
        first_name="John",
        city="New York",
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact_id,
        campaign_id=campaign_id,
        current_state="cold" if status == "pending" else "warm",
        conversation_stage="trust",
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
        max_first_message_length=200,
    )
    account = TelegramAccount(
        id=uuid.uuid4(),
        phone="+123",
        status="ready",
        daily_messages_sent=0,
        session_string="sess",
    )
    return cc, contact, conversation, script, account


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

    async def test_pending_contact_with_started_conversation_is_not_greeted_again(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact
        from app.models.conversation import Conversation

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)
        sample_contact.telegram_user_id = 123456

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        conversation = Conversation(
            id=uuid.uuid4(),
            contact_id=sample_contact.id,
            campaign_id=sample_campaign.id,
            current_state="cold",
            last_message_at=datetime.now(timezone.utc),
        )

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([conversation]),
        ]

        with patch(
            "app.core.scheduler.send_initial_message", new_callable=AsyncMock
        ) as mock_send:
            await process_campaigns(mock_db)

        mock_send.assert_not_awaited()
        assert cc.status == "replied"
        assert cc.reply_received_at is not None

    async def test_follow_up_without_conversation_context_is_skipped(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)
        sample_contact.telegram_user_id = 123456

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="initial_sent",
            message_count=1,
            initial_sent_at=datetime.now(timezone.utc) - timedelta(hours=25),
        )

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([]),
        ]

        with patch(
            "app.core.scheduler.send_follow_up_message", new_callable=AsyncMock
        ) as mock_send:
            await process_campaigns(mock_db)

        mock_send.assert_not_awaited()

    async def test_follow_up_is_not_sent_after_reply_or_operator_touch(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact
        from app.models.conversation import Conversation

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)
        sample_contact.telegram_user_id = 123456

        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="initial_sent",
            message_count=1,
            initial_sent_at=datetime.now(timezone.utc) - timedelta(hours=25),
            reply_received_at=datetime.now(timezone.utc),
        )
        conversation = Conversation(
            id=uuid.uuid4(),
            contact_id=sample_contact.id,
            campaign_id=sample_campaign.id,
            current_state="warm",
            operator_status=None,
        )

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([conversation]),
        ]

        with patch(
            "app.core.scheduler.send_follow_up_message", new_callable=AsyncMock
        ) as mock_send:
            await process_campaigns(mock_db)

        mock_send.assert_not_awaited()

        cc.reply_received_at = None
        conversation.operator_status = "qualified"
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([conversation]),
        ]

        with patch(
            "app.core.scheduler.send_follow_up_message", new_callable=AsyncMock
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
        sample_contact.telegram_username = None

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

    async def test_contact_with_username_only_is_sent(
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
        sample_contact.telegram_username = "username_only"

        account = MockTelegramAccount()

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
            mock_send.assert_awaited_once()
            assert mock_send.call_args.kwargs["contact"].telegram_username == "username_only"

    async def test_invalid_contact_peer_is_not_retried(
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
        sample_contact.status = "invalid_peer"
        sample_contact.is_valid = "invalid"

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

        assert cc.status == "invalid_peer"
        mock_db.commit.assert_awaited_once()

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

    async def test_invalid_peer_marks_contact_and_continues(
        self, mock_db, sample_script
    ):
        from app.models.campaign import Campaign, CampaignContact
        from app.models.contact import Contact

        campaign1 = Campaign(
            id=uuid.uuid4(),
            script_id=sample_script.id,
            name="Broken peer campaign",
            status="running",
        )
        campaign2 = Campaign(
            id=uuid.uuid4(),
            script_id=sample_script.id,
            name="Next campaign",
            status="running",
        )
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)

        contact1 = Contact(
            id=uuid.uuid4(),
            telegram_user_id=111,
            first_name="Bad",
        )
        contact2 = Contact(
            id=uuid.uuid4(),
            telegram_user_id=222,
            first_name="Good",
        )
        cc1 = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=campaign1.id,
            contact_id=contact1.id,
            status="pending",
            message_count=0,
        )
        cc2 = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=campaign2.id,
            contact_id=contact2.id,
            status="pending",
            message_count=0,
        )
        account = MockTelegramAccount()

        mock_db.execute.side_effect = [
            _SimpleMockResult([campaign1, campaign2]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc1]),
            _SimpleMockResult([contact1]),
            _SimpleMockResult([]),
            _SimpleMockResult([account]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc2]),
            _SimpleMockResult([contact2]),
            _SimpleMockResult([]),
            _SimpleMockResult([account]),
        ]

        send_calls = []

        async def fake_send_initial(**kwargs):
            send_calls.append(kwargs["contact"].id)
            if kwargs["contact"].id == contact1.id:
                raise ContactPeerInvalidError(
                    kwargs["account"].id,
                    kwargs["contact"].id,
                    kwargs["contact"].telegram_user_id,
                )

        with patch(
            "app.core.scheduler.send_initial_message",
            side_effect=fake_send_initial,
        ):
            await process_campaigns(mock_db)

        assert send_calls == [contact1.id, contact2.id]
        assert cc1.status == "invalid_peer"
        assert contact1.status == "invalid_peer"
        assert contact1.is_valid == "invalid"
        assert cc2.status == "pending"
        assert mock_db.commit.await_count >= 2

    async def test_generic_send_error_rolls_back_and_continues_next_campaign(
        self, sample_script
    ):
        from app.models.campaign import Campaign, CampaignContact
        from app.models.contact import Contact

        class RollbackAwareSession:
            def __init__(self):
                self.rolled_back = False
                self.execute = AsyncMock()
                self.commit = AsyncMock()
                self.add = MagicMock()

            async def rollback(self):
                self.rolled_back = True

        class RollbackAwareCampaign:
            def __init__(self, campaign):
                self._campaign = campaign

            @property
            def id(self):
                return self._campaign.id

            @property
            def script_id(self):
                if mock_db.rolled_back:
                    raise AssertionError("expired campaign state was touched")
                return self._campaign.script_id

            @property
            def processed_contacts(self):
                return self._campaign.processed_contacts

            @processed_contacts.setter
            def processed_contacts(self, value):
                self._campaign.processed_contacts = value

        campaign1 = Campaign(
            id=uuid.uuid4(),
            script_id=sample_script.id,
            name="Fails",
            status="running",
        )
        campaign2 = Campaign(
            id=uuid.uuid4(),
            script_id=sample_script.id,
            name="Still runs",
            status="running",
        )
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)

        contact1 = Contact(id=uuid.uuid4(), telegram_user_id=111)
        contact2 = Contact(id=uuid.uuid4(), telegram_user_id=222)
        cc1 = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=campaign1.id,
            contact_id=contact1.id,
            status="pending",
            message_count=0,
        )
        cc2 = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=campaign2.id,
            contact_id=contact2.id,
            status="pending",
            message_count=0,
        )
        account = MockTelegramAccount()
        mock_db = RollbackAwareSession()
        wrapped_campaigns = [
            RollbackAwareCampaign(campaign1),
            RollbackAwareCampaign(campaign2),
        ]
        mock_db.execute.side_effect = [
            _SimpleMockResult(wrapped_campaigns),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc1]),
            _SimpleMockResult([contact1]),
            _SimpleMockResult([]),
            _SimpleMockResult([account]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc2]),
            _SimpleMockResult([contact2]),
            _SimpleMockResult([]),
            _SimpleMockResult([account]),
        ]

        send_calls = []

        async def fake_send_initial(**kwargs):
            send_calls.append(kwargs["contact"].telegram_user_id)
            if kwargs["contact"].telegram_user_id == 111:
                raise RuntimeError("temporary send failure")

        with patch(
            "app.core.scheduler.send_initial_message",
            side_effect=fake_send_initial,
        ):
            await process_campaigns(mock_db)

        assert mock_db.rolled_back is True
        assert send_calls == [111, 222]

    async def test_missing_script_contact_terminal_conversation_and_no_account_skip(
        self, mock_db, sample_campaign, sample_script, sample_contact, sample_conversation
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

        # Missing script exits before contact lookup.
        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([]),
        ]
        await process_campaigns(mock_db)

        # Missing contact skips send.
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([]),
        ]
        with patch("app.core.scheduler.send_initial_message", new_callable=AsyncMock) as mock_send:
            await process_campaigns(mock_db)
        mock_send.assert_not_awaited()

        # Terminal conversation skips send.
        sample_conversation.current_state = "meeting_booked"
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([sample_conversation]),
        ]
        with patch("app.core.scheduler.send_initial_message", new_callable=AsyncMock) as mock_send:
            await process_campaigns(mock_db)
        mock_send.assert_not_awaited()

        # No eligible account skips send.
        sample_conversation.current_state = "cold"
        mock_db.execute.reset_mock()
        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([sample_conversation]),
            _SimpleMockResult([]),
        ]
        with patch("app.core.account_manager.select_account", return_value=None):
            with patch("app.core.scheduler.send_initial_message", new_callable=AsyncMock) as mock_send:
                await process_campaigns(mock_db)
        mock_send.assert_not_awaited()

    async def test_assigned_account_is_used_when_eligible(
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
        assigned_account = TelegramAccount(
            id=uuid.uuid4(),
            phone="+111",
            status="ready",
            session_string="sess",
        )
        sample_contact.telegram_user_id = 123456
        sample_contact.assigned_account_id = assigned_account.id

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([]),
            _SimpleMockResult([assigned_account]),
        ]

        with patch("app.core.scheduler.send_initial_message", new_callable=AsyncMock) as mock_send:
            await process_campaigns(mock_db)

        mock_send.assert_awaited_once()
        assert mock_send.call_args.kwargs["account"] is assigned_account

    async def test_process_campaigns_handles_naive_now_inside_contact_loop(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)
        sample_contact.telegram_user_id = 123456
        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        account = MockTelegramAccount()

        mock_db.execute.side_effect = [
            _SimpleMockResult([sample_campaign]),
            _SimpleMockResult([sample_script]),
            _SimpleMockResult([cc]),
            _SimpleMockResult([sample_contact]),
            _SimpleMockResult([]),
            _SimpleMockResult([account]),
        ]

        with (
            patch("app.core.scheduler.datetime") as mock_datetime,
            patch("app.core.scheduler.send_initial_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0)
            await process_campaigns(mock_db)

        mock_send.assert_awaited_once()

    async def test_flood_retry_paths_mark_cooldown_and_alternatives(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)
        sample_contact.telegram_user_id = 123456
        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        first_account = MockTelegramAccount()
        retry_account = MockTelegramAccount()

        async def run_with(send_side_effect, retry_results):
            mock_db.reset_mock()
            mock_db.execute.side_effect = [
                _SimpleMockResult([sample_campaign]),
                _SimpleMockResult([sample_script]),
                _SimpleMockResult([cc]),
                _SimpleMockResult([sample_contact]),
                _SimpleMockResult([]),
                _SimpleMockResult([first_account]),
                _SimpleMockResult(retry_results),
            ]
            with patch(
                "app.core.account_manager.mark_account_cooldown",
                new_callable=AsyncMock,
            ) as mock_cooldown:
                with patch(
                    "app.core.account_manager.select_account",
                    side_effect=[first_account, retry_results[0] if retry_results else None],
                ):
                    with patch(
                        "app.core.scheduler.send_initial_message",
                        new=AsyncMock(side_effect=send_side_effect),
                    ) as mock_send:
                        await process_campaigns(mock_db)
            return mock_cooldown, mock_send

        cooldown, send = await run_with(
            [AccountFloodError(first_account.id, wait_seconds=7)],
            [],
        )
        assert cooldown.await_count == 1
        assert send.await_count == 1

        cooldown, send = await run_with(
            [
                AccountFloodError(first_account.id, wait_seconds=7),
                AccountFloodError(retry_account.id, wait_seconds=9),
            ],
            [retry_account],
        )
        assert cooldown.await_count == 2
        assert send.await_count == 2

    async def test_peer_flood_retry_paths_mark_cooldown_and_alternatives(
        self, mock_db, sample_campaign, sample_script, sample_contact
    ):
        from app.models.campaign import CampaignContact

        sample_campaign.status = "running"
        sample_script.working_hours_start = time(0, 0)
        sample_script.working_hours_end = time(23, 59)
        sample_contact.telegram_user_id = 123456
        cc = CampaignContact(
            id=uuid.uuid4(),
            campaign_id=sample_campaign.id,
            contact_id=sample_contact.id,
            status="pending",
            message_count=0,
        )
        first_account = MockTelegramAccount()
        retry_account = MockTelegramAccount()

        async def run_with(send_side_effect, retry_results):
            mock_db.reset_mock()
            mock_db.execute.side_effect = [
                _SimpleMockResult([sample_campaign]),
                _SimpleMockResult([sample_script]),
                _SimpleMockResult([cc]),
                _SimpleMockResult([sample_contact]),
                _SimpleMockResult([]),
                _SimpleMockResult([first_account]),
                _SimpleMockResult(retry_results),
            ]
            with patch(
                "app.core.account_manager.mark_account_cooldown",
                new_callable=AsyncMock,
            ) as mock_cooldown:
                with patch(
                    "app.core.account_manager.select_account",
                    side_effect=[first_account, retry_results[0] if retry_results else None],
                ):
                    with patch(
                        "app.core.scheduler.send_initial_message",
                        new=AsyncMock(side_effect=send_side_effect),
                    ) as mock_send:
                        await process_campaigns(mock_db)
            return mock_cooldown, mock_send

        cooldown, send = await run_with([AccountPeerFloodError(first_account.id)], [])
        assert cooldown.await_count == 1
        assert send.await_count == 1

        cooldown, send = await run_with(
            [AccountPeerFloodError(first_account.id), AccountPeerFloodError(retry_account.id)],
            [retry_account],
        )
        assert cooldown.await_count == 2
        assert send.await_count == 2


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
                assert client_inst.send_message.call_args.kwargs["user_id"] == 123456
                client_inst.stop.assert_awaited_once()

    async def test_successful_send_prefers_username(self, mock_db):
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
            telegram_username="leaduser",
            first_name="John",
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

        with patch("app.llm.engine.LLMEngine") as MockEngine:
            engine_inst = MockEngine.return_value
            engine_inst.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "Hello!", "model": "gpt-4", "tokens_used": 10}
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

        assert client_inst.send_message.call_args.kwargs["user_id"] == "leaduser"

    async def test_initial_message_uses_approved_preview_without_llm(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects()
        cc.preview_message = "Привет, John. Это одобренный предпросмотр."

        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=0),
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_initial_message(mock_db, cc, contact, conversation, script, account)

        MockEngine.assert_not_called()
        sent_text = client_inst.send_message.call_args.kwargs["text"]
        assert sent_text == "Привет, John. Это одобренный предпросмотр."
        assert cc.status == "initial_sent"

    async def test_stale_username_retries_telegram_user_id(self, mock_db, monkeypatch):
        class FakeUsernameInvalid(Exception):
            pass

        monkeypatch.setattr("app.core.scheduler.UsernameInvalid", FakeUsernameInvalid)
        cc, contact, conversation, script, account = _build_send_objects()

        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=0),
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "Hello", "model": "gpt", "tokens_used": 1}
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(
                side_effect=[FakeUsernameInvalid("bad username"), {"message_id": 1}]
            )
            client_inst.stop = AsyncMock()

            await send_initial_message(mock_db, cc, contact, conversation, script, account)

        assert client_inst.send_message.await_args_list[0].kwargs["user_id"] == "leaduser"
        assert client_inst.send_message.await_args_list[1].kwargs["user_id"] == 123456
        assert cc.status == "initial_sent"

    async def test_initial_message_retries_robotic_crypto_language(self, mock_db):
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
            first_name="Максим",
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

        with patch("app.llm.engine.LLMEngine") as MockEngine:
            engine_inst = MockEngine.return_value
            engine_inst.generate_response_with_guardrails = AsyncMock(
                side_effect=[
                    {
                        "text": "Привет. Помогаем выводить криптовалюту в фиат.",
                        "model": "gpt-4",
                        "tokens_used": 10,
                    },
                    {
                        "text": "Привет, Максим. Как сейчас обрабатываете новые заявки?",
                        "model": "gpt-4",
                        "tokens_used": 7,
                    },
                ]
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

        assert engine_inst.generate_response_with_guardrails.await_count == 2
        sent_text = client_inst.send_message.call_args.kwargs["text"]
        assert "выводить криптовалюту" not in sent_text.lower()
        assert "Как сейчас обрабатываете" in sent_text

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

    async def test_llm_exception_is_reraised(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects()

        with patch("app.llm.engine.LLMEngine") as MockEngine:
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                side_effect=RuntimeError("llm down")
            )
            with pytest.raises(RuntimeError, match="llm down"):
                await send_initial_message(mock_db, cc, contact, conversation, script, account)

    async def test_fallback_model_uses_safe_initial_text(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects()
        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=0),
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "fallback raw", "model": "fallback", "tokens_used": 99}
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_initial_message(mock_db, cc, contact, conversation, script, account)

        sent_text = client_inst.send_message.call_args.kwargs["text"]
        assert "fallback raw" not in sent_text
        assert "John" in sent_text

    async def test_initial_quality_retry_falls_back_when_retry_is_still_bad(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects()
        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=0),
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                side_effect=[
                    {"text": "Как у вас в Рогах и копытах устроен стек?", "model": "gpt", "tokens_used": 1},
                    {"text": "Как у вас в Рогах и копытах устроен стек?", "model": "gpt", "tokens_used": 1},
                ]
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_initial_message(mock_db, cc, contact, conversation, script, account)

        sent_text = client_inst.send_message.call_args.kwargs["text"]
        assert "Рогах и копытах" not in sent_text

    async def test_initial_quality_retry_exception_uses_safe_fallback(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects()
        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=0),
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                side_effect=[
                    {"text": "Как у вас в Рогах и копытах устроен стек?", "model": "gpt", "tokens_used": 1},
                    RuntimeError("retry failed"),
                ]
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_initial_message(mock_db, cc, contact, conversation, script, account)

        sent_text = client_inst.send_message.call_args.kwargs["text"]
        assert "Рогах и копытах" not in sent_text

    async def test_initial_send_multiple_chunks_waits_between_chunks(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects()
        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=100),
            patch("app.core.humanizer.split_message_into_chunks", return_value=["one", "two"]),
            patch("app.core.humanizer.chunk_pause_seconds", return_value=0.01),
            patch("app.core.scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "one two", "model": "gpt", "tokens_used": 1}
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_initial_message(mock_db, cc, contact, conversation, script, account)

        assert client_inst.send_message.await_count == 2
        mock_sleep.assert_awaited_once_with(0.01)

    async def test_initial_send_translates_telegram_exceptions(self, mock_db, monkeypatch):
        class FakeFlood(Exception):
            value = 12

        class FakePeerFlood(Exception):
            pass

        class FakePeerInvalid(Exception):
            pass

        monkeypatch.setattr("app.core.scheduler.FloodWait", FakeFlood)
        monkeypatch.setattr("app.core.scheduler.PeerFlood", FakePeerFlood)
        monkeypatch.setattr("app.core.scheduler.PeerIdInvalid", FakePeerInvalid)

        async def run_with(exc, expected):
            cc, contact, conversation, script, account = _build_send_objects()
            with (
                patch("app.llm.engine.LLMEngine") as MockEngine,
                patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
                patch("app.core.humanizer.calculate_typing_delay", return_value=0),
                patch("app.bots.seller_client.SellerClient") as MockClient,
            ):
                MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                    return_value={"text": "Hello", "model": "gpt", "tokens_used": 1}
                )
                client_inst = MockClient.return_value
                client_inst.start = AsyncMock()
                client_inst.send_message = AsyncMock(side_effect=exc)
                client_inst.stop = AsyncMock()
                with pytest.raises(expected):
                    await send_initial_message(
                        mock_db, cc, contact, conversation, script, account
                    )
                client_inst.stop.assert_awaited_once()

        await run_with(FakeFlood("flood"), AccountFloodError)
        await run_with(FakePeerFlood("peer"), AccountPeerFloodError)
        await run_with(FakePeerInvalid("invalid"), ContactPeerInvalidError)

    async def test_initial_send_logs_cache_invalidation_failure(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects()
        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=0),
            patch("app.db.redis.get_redis", new=AsyncMock(side_effect=RuntimeError("redis down"))),
            patch("app.core.scheduler.logger.debug") as mock_debug,
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "Hello", "model": "gpt", "tokens_used": 1}
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_initial_message(mock_db, cc, contact, conversation, script, account)

        assert mock_debug.called


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

    async def test_follow_up_uses_last_agent_message_and_multiple_chunks(self, mock_db):
        from app.models.conversation import Message

        cc, contact, conversation, script, account = _build_send_objects(
            status="initial_sent"
        )
        history = [
            Message(direction="inbound", content="Интересно"),
            Message(direction="outbound", content="Последний ответ менеджера"),
        ]

        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch(
                "app.services.conversation_service.get_conversation_context",
                new_callable=AsyncMock,
            ) as mock_ctx,
            patch("app.llm.prompts.build_follow_up_user_prompt", return_value="prompt") as mock_prompt,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=100),
            patch("app.core.humanizer.split_message_into_chunks", return_value=["one", "two"]),
            patch("app.core.humanizer.chunk_pause_seconds", return_value=0.01),
            patch("app.core.scheduler.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            mock_ctx.return_value = {"messages": history, "facts": {"company": "Acme"}}
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "one two", "model": "gpt", "tokens_used": 1}
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_follow_up_message(mock_db, cc, contact, conversation, script, account)

        assert mock_prompt.call_args.kwargs["last_agent_message"] == "Последний ответ менеджера"
        assert client_inst.send_message.await_count == 2
        mock_sleep.assert_awaited_once_with(0.01)

    async def test_follow_up_llm_exception_and_empty_text_are_errors(self, mock_db):
        for response, expected in [
            (RuntimeError("llm down"), RuntimeError),
            ({"text": "", "model": "gpt", "tokens_used": 0}, RuntimeError),
        ]:
            cc, contact, conversation, script, account = _build_send_objects(
                status="initial_sent"
            )
            with (
                patch("app.llm.engine.LLMEngine") as MockEngine,
                patch(
                    "app.services.conversation_service.get_conversation_context",
                    new_callable=AsyncMock,
                ) as mock_ctx,
            ):
                mock_ctx.return_value = {"messages": [], "facts": {}}
                if isinstance(response, Exception):
                    MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                        side_effect=response
                    )
                    match = "llm down"
                else:
                    MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                        return_value=response
                    )
                    match = "LLM returned empty text"
                with pytest.raises(expected, match=match):
                    await send_follow_up_message(
                        mock_db, cc, contact, conversation, script, account
                    )

    async def test_follow_up_translates_telegram_exceptions(self, mock_db, monkeypatch):
        class FakeFlood(Exception):
            value = 13

        class FakePeerFlood(Exception):
            pass

        class FakePeerInvalid(Exception):
            pass

        monkeypatch.setattr("app.core.scheduler.FloodWait", FakeFlood)
        monkeypatch.setattr("app.core.scheduler.PeerFlood", FakePeerFlood)
        monkeypatch.setattr("app.core.scheduler.PeerIdInvalid", FakePeerInvalid)

        async def run_with(exc, expected):
            cc, contact, conversation, script, account = _build_send_objects(
                status="initial_sent"
            )
            with (
                patch("app.llm.engine.LLMEngine") as MockEngine,
                patch(
                    "app.services.conversation_service.get_conversation_context",
                    new_callable=AsyncMock,
                ) as mock_ctx,
                patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
                patch("app.core.humanizer.calculate_typing_delay", return_value=0),
                patch("app.bots.seller_client.SellerClient") as MockClient,
            ):
                mock_ctx.return_value = {"messages": [], "facts": {}}
                MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                    return_value={"text": "Follow up", "model": "gpt", "tokens_used": 1}
                )
                client_inst = MockClient.return_value
                client_inst.start = AsyncMock()
                client_inst.send_message = AsyncMock(side_effect=exc)
                client_inst.stop = AsyncMock()
                with pytest.raises(expected):
                    await send_follow_up_message(
                        mock_db, cc, contact, conversation, script, account
                    )
                client_inst.stop.assert_awaited_once()

        await run_with(FakeFlood("flood"), AccountFloodError)
        await run_with(FakePeerFlood("peer"), AccountPeerFloodError)
        await run_with(FakePeerInvalid("invalid"), ContactPeerInvalidError)

    async def test_follow_up_logs_cache_invalidation_failure(self, mock_db):
        cc, contact, conversation, script, account = _build_send_objects(
            status="initial_sent"
        )
        with (
            patch("app.llm.engine.LLMEngine") as MockEngine,
            patch(
                "app.services.conversation_service.get_conversation_context",
                new_callable=AsyncMock,
            ) as mock_ctx,
            patch("app.core.humanizer.calculate_thinking_delay", return_value=0),
            patch("app.core.humanizer.calculate_typing_delay", return_value=0),
            patch("app.db.redis.get_redis", new=AsyncMock(side_effect=RuntimeError("redis down"))),
            patch("app.core.scheduler.logger.debug") as mock_debug,
            patch("app.bots.seller_client.SellerClient") as MockClient,
        ):
            mock_ctx.return_value = {"messages": [], "facts": {}}
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "Follow up", "model": "gpt", "tokens_used": 1}
            )
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.send_message = AsyncMock(return_value={"message_id": 1})
            client_inst.stop = AsyncMock()

            await send_follow_up_message(mock_db, cc, contact, conversation, script, account)

        assert mock_debug.called


@pytest.mark.asyncio
async def test_auto_close_conversations_closes_stale_contacts(mock_db, sample_conversation):
    from app.models.campaign import CampaignContact

    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=sample_conversation.campaign_id,
        contact_id=sample_conversation.contact_id,
        status="follow_up_sent",
        follow_up_sent_at=datetime.now(timezone.utc) - timedelta(hours=72),
    )
    sample_conversation.current_state = "follow_up"
    mock_db.execute.side_effect = [
        _SimpleMockResult([cc]),
        _SimpleMockResult([sample_conversation]),
    ]

    await scheduler_module.auto_close_conversations(mock_db)

    assert cc.status == "closed"
    assert sample_conversation.current_state == "closed"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_auto_close_conversations_handles_missing_conversation(mock_db):
    from app.models.campaign import CampaignContact

    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        contact_id=uuid.uuid4(),
        status="follow_up_sent",
        follow_up_sent_at=datetime.now(timezone.utc) - timedelta(hours=72),
    )
    mock_db.execute.side_effect = [_SimpleMockResult([cc]), _SimpleMockResult([])]

    await scheduler_module.auto_close_conversations(mock_db)

    assert cc.status == "closed"
    mock_db.commit.assert_awaited_once()


class TestCampaignScheduler:
    def test_get_sync_db_url_converts_plain_postgres(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.scheduler.get_settings",
            lambda: MagicMock(database_url="postgresql://user:pass@host/db"),
        )

        assert _get_sync_db_url().startswith("postgresql+psycopg2://")

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

    @pytest.mark.asyncio
    async def test_scheduler_job_wrappers_log_exceptions(self):
        class BrokenSession:
            async def __aenter__(self):
                raise RuntimeError("session down")

            async def __aexit__(self, exc_type, exc, tb):
                return False

        with patch("app.core.scheduler.AsyncSessionLocal", return_value=BrokenSession()):
            with patch("app.core.scheduler.logger.exception") as mock_exception:
                await CampaignScheduler._run_process_campaigns()
                await CampaignScheduler._run_reset_daily_counters()
                await CampaignScheduler._run_recover_cooldown_accounts()
                await CampaignScheduler._run_auto_close_conversations()

        assert mock_exception.call_count == 4

    @pytest.mark.asyncio
    async def test_scheduler_job_wrappers_success_paths(self, monkeypatch):
        session = AsyncMock()

        class SessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr("app.core.scheduler.AsyncSessionLocal", lambda: SessionContext())
        monkeypatch.setattr("app.core.scheduler.process_campaigns", AsyncMock())
        monkeypatch.setattr(
            "app.core.account_manager.reset_daily_counters_db", AsyncMock()
        )
        monkeypatch.setattr(
            "app.core.account_manager.recover_cooldown_accounts", AsyncMock()
        )
        monkeypatch.setattr("app.core.scheduler.auto_close_conversations", AsyncMock())

        await CampaignScheduler._run_process_campaigns()
        await CampaignScheduler._run_reset_daily_counters()
        await CampaignScheduler._run_recover_cooldown_accounts()
        await CampaignScheduler._run_auto_close_conversations()


def test_scheduler_import_sets_event_loop_when_missing():
    original_account_flood = AccountFloodError
    original_account_peer_flood = AccountPeerFloodError
    original_contact_peer_invalid = ContactPeerInvalidError
    loop = asyncio.new_event_loop()
    try:
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            with patch("asyncio.new_event_loop", return_value=loop) as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    importlib.reload(scheduler_module)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(loop)
    finally:
        importlib.reload(scheduler_module)
        scheduler_module.AccountFloodError = original_account_flood
        scheduler_module.AccountPeerFloodError = original_account_peer_flood
        scheduler_module.ContactPeerInvalidError = original_contact_peer_invalid
        loop.close()
