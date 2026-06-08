"""Tests for operator notification stubs."""

import uuid
from datetime import datetime

import pytest

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.services.notification_service import (
    notify_operator_hot_lead,
    notify_operator_meeting_booked,
)


@pytest.fixture
def dummy_contact():
    return Contact(
        id=uuid.uuid4(),
        telegram_username="testuser",
        phone="+123",
        first_name="John",
        status="new",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def dummy_conversation():
    return Conversation(
        id=uuid.uuid4(),
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        current_state="hot",
        facts_extracted={},
        created_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_notify_operator_hot_lead_runs_without_error(dummy_contact, dummy_conversation):
    result = await notify_operator_hot_lead(dummy_contact, dummy_conversation)
    assert result is None


@pytest.mark.asyncio
async def test_notify_operator_meeting_booked_runs_without_error(dummy_contact, dummy_conversation):
    result = await notify_operator_meeting_booked(dummy_contact, dummy_conversation)
    assert result is None
