"""Tests for conversation service business logic."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.models.conversation import Conversation, Message
from app.services.conversation_service import (
    add_message,
    get_conversation_context,
    update_lead_facts,
)
from tests.conftest import MockResult, build_mock_session


@pytest.mark.asyncio
async def test_get_conversation_context_returns_messages_and_facts():
    conv_id = uuid.uuid4()
    msg1 = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        direction="outbound",
        content="Hello",
        sent_at=datetime(2024, 1, 1, 10, 0, 0),
    )
    msg2 = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        direction="inbound",
        content="Hi there",
        sent_at=datetime(2024, 1, 1, 10, 1, 0),
    )
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        facts_extracted={"budget": "10k"},
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([msg2, msg1]),  # messages ordered desc
        MockResult([conversation]),  # conversation lookup
    ]

    result = await get_conversation_context(mock_db, conv_id, limit=10)

    assert result["messages"] == [msg1, msg2]  # reversed back to chronological
    assert result["facts"] == {"budget": "10k"}


@pytest.mark.asyncio
async def test_get_conversation_context_returns_cached_messages(monkeypatch):
    conv_id = uuid.uuid4()
    redis = object()

    async def fake_get_redis():
        return redis

    async def fake_get_cached_conversation_context(redis_arg, conversation_id):
        assert redis_arg is redis
        assert conversation_id == conv_id
        return {
            "messages": [
                {
                    "id": "msg-1",
                    "direction": "inbound",
                    "content": "Cached hi",
                }
            ],
            "facts": {"city": "Moscow"},
        }

    monkeypatch.setattr(
        "app.services.conversation_service.get_redis", fake_get_redis
    )
    monkeypatch.setattr(
        "app.services.conversation_service.get_cached_conversation_context",
        fake_get_cached_conversation_context,
    )
    mock_db = build_mock_session()

    result = await get_conversation_context(mock_db, conv_id)

    assert result["messages"][0].content == "Cached hi"
    assert result["facts"] == {"city": "Moscow"}
    mock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_conversation_context_falls_back_when_cache_read_and_write_fail(
    monkeypatch,
):
    conv_id = uuid.uuid4()
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        direction="outbound",
        content="Hello",
        sent_at=datetime(2024, 1, 1, 10, 0, 0),
    )
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        facts_extracted={},
    )
    calls = 0

    async def flaky_get_redis():
        nonlocal calls
        calls += 1
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        "app.services.conversation_service.get_redis", flaky_get_redis
    )
    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([msg]),
        MockResult([conversation]),
    ]

    result = await get_conversation_context(mock_db, conv_id)

    assert result["messages"] == [msg]
    assert result["facts"] == {}
    assert calls == 2


@pytest.mark.asyncio
async def test_add_message_inserts_and_updates_timestamp():
    conv_id = uuid.uuid4()
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
    )

    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([conversation])
    mock_db.refresh = AsyncMock()

    message = await add_message(
        mock_db,
        conversation_id=conv_id,
        direction="outbound",
        content="Test message",
        message_type="text",
    )

    assert message.conversation_id == conv_id
    assert message.direction == "outbound"
    assert message.content == "Test message"
    assert conversation.last_message_at is not None
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(message)


@pytest.mark.asyncio
async def test_add_message_succeeds_without_conversation_and_cache(monkeypatch):
    conv_id = uuid.uuid4()
    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([])
    mock_db.refresh = AsyncMock()

    async def failing_get_redis():
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        "app.services.conversation_service.get_redis", failing_get_redis
    )

    message = await add_message(
        mock_db,
        conversation_id=conv_id,
        direction="inbound",
        content="No conversation row yet",
    )

    assert message.conversation_id == conv_id
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(message)


@pytest.mark.asyncio
async def test_update_lead_facts_merges_jsonb():
    conv_id = uuid.uuid4()
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        facts_extracted={"budget": "10k"},
    )

    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([conversation])
    mock_db.refresh = AsyncMock()

    updated = await update_lead_facts(
        mock_db, conv_id, {"needs": "CRM", "budget": "15k"}
    )

    assert updated.facts_extracted == {"budget": "15k", "needs": "CRM"}
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(conversation)


@pytest.mark.asyncio
async def test_update_lead_facts_succeeds_when_cache_invalidation_fails(monkeypatch):
    conv_id = uuid.uuid4()
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        facts_extracted=None,
    )
    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([conversation])
    mock_db.refresh = AsyncMock()

    async def failing_get_redis():
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        "app.services.conversation_service.get_redis", failing_get_redis
    )

    updated = await update_lead_facts(mock_db, conv_id, {"budget": "15k"})

    assert updated.facts_extracted == {"budget": "15k"}
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_lead_facts_raises_when_conversation_missing():
    conv_id = uuid.uuid4()
    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([])

    with pytest.raises(ValueError, match=f"Conversation {conv_id} not found"):
        await update_lead_facts(mock_db, conv_id, {"needs": "CRM"})
