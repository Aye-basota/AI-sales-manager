from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.scheduler import (
    should_send_to_contact,
    is_within_working_hours,
    next_contact_to_process,
)


class TestShouldSendToContact:
    def test_pending_always_ready(self):
        assert should_send_to_contact("pending", None, 24, datetime.now()) is True
        assert should_send_to_contact("pending", datetime.now(), 24, datetime.now()) is True

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
        assert is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now) is True

    def test_at_start_boundary(self):
        now = datetime(2024, 1, 1, 9, 0, 0)
        assert is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now) is True

    def test_at_end_boundary(self):
        now = datetime(2024, 1, 1, 18, 0, 0)
        assert is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now) is True

    def test_before_start(self):
        now = datetime(2024, 1, 1, 8, 59, 0)
        assert is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now) is False

    def test_after_end(self):
        now = datetime(2024, 1, 1, 18, 1, 0)
        assert is_within_working_hours("Europe/Moscow", time(9, 0), time(18, 0), now) is False

    def test_overnight_shift(self):
        now = datetime(2024, 1, 1, 23, 0, 0)
        assert is_within_working_hours("Europe/Moscow", time(22, 0), time(6, 0), now) is True


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
