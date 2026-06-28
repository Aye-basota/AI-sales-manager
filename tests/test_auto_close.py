"""Tests for auto-close stale conversations after 48h."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.scheduler import auto_close_conversations
from app.models.campaign import CampaignContact
from app.models.conversation import Conversation


def _make_result(items=None, single=None):
    class Scalars:
        def all(self):
            return items or []

    class Result:
        def scalars(self, *args, **kwargs):
            return Scalars()

        def scalar_one_or_none(self):
            return single

    return Result()


@pytest.mark.asyncio
async def test_auto_close_stale_follow_ups():
    contact_id = uuid4()
    campaign_id = uuid4()

    stale_cc = CampaignContact(
        id=uuid4(),
        campaign_id=campaign_id,
        contact_id=contact_id,
        status="follow_up_sent",
        follow_up_sent_at=datetime.now() - timedelta(hours=49),
    )
    conversation = Conversation(
        id=uuid4(),
        contact_id=contact_id,
        campaign_id=campaign_id,
        current_state="follow_up",
    )

    mock_db = MagicMock()
    calls = [
        _make_result([stale_cc]),
        _make_result(single=conversation),
    ]
    mock_db.execute = AsyncMock(side_effect=calls)
    mock_db.commit = AsyncMock()

    await auto_close_conversations(mock_db)

    assert stale_cc.status == "closed"
    assert conversation.current_state == "closed"


@pytest.mark.asyncio
async def test_auto_close_ignores_recent_follow_ups():
    """When the DB returns no stale contacts, nothing is closed."""
    mock_db = MagicMock()
    calls = [
        _make_result([]),
    ]
    mock_db.execute = AsyncMock(side_effect=calls)
    mock_db.commit = AsyncMock()

    await auto_close_conversations(mock_db)

    mock_db.commit.assert_awaited_once()
