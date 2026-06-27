"""Tests for lead discovery adapters."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.lead_discovery import (
    LeadCriteria,
    DiscoveredContact,
    GenericJSONAdapter,
    RosprofileAdapter,
    TelegramPublicSearch,
    ChannelMembersParser,
    enrich_contact,
    discover_leads,
)


@pytest.fixture
def mock_pyrogram_user():
    user = MagicMock()
    user.id = 123456
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_deleted = False
    user.bio = "CEO at TestCorp"
    return user


@pytest.fixture
def mock_pyrogram_message(mock_pyrogram_user):
    msg = MagicMock()
    msg.from_user = mock_pyrogram_user
    return msg


# ---------------------------------------------------------------------------
# GenericJSONAdapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generic_json_adapter_empty_when_no_url():
    adapter = GenericJSONAdapter(api_url="", api_key="")
    result = await adapter.search(LeadCriteria(query="ceo", limit=10))
    assert result == []


@pytest.mark.asyncio
async def test_generic_json_adapter_parses_response():
    adapter = GenericJSONAdapter(api_url="http://example.com/api", api_key="secret")
    response_data = {
        "results": [
            {
                "telegram_username": "john_doe",
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme",
                "job_title": "CEO",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await adapter.search(LeadCriteria(query="ceo", limit=10))

    assert len(result) == 1
    assert result[0].telegram_username == "john_doe"
    assert result[0].company_name == "Acme"
    assert result[0].position == "CEO"


@pytest.mark.asyncio
async def test_generic_json_adapter_handles_error():
    adapter = GenericJSONAdapter(api_url="http://example.com/api")
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await adapter.search(LeadCriteria(query="ceo"))
    assert result == []


# ---------------------------------------------------------------------------
# RosprofileAdapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rosprofile_adapter_is_generic():
    adapter = RosprofileAdapter(api_url="http://rosprofile.test/api")
    assert isinstance(adapter, GenericJSONAdapter)


# ---------------------------------------------------------------------------
# TelegramPublicSearch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_telegram_public_search_no_pyrogram():
    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", False):
        searcher = TelegramPublicSearch()
        result = await searcher.search("ceo", limit=10)
        assert result == []


@pytest.mark.asyncio
async def test_telegram_public_search_with_mock_client(mock_pyrogram_message):
    mock_client = MagicMock()
    mock_client.search_global = AsyncMock(return_value=[mock_pyrogram_message])

    searcher = TelegramPublicSearch(client=mock_client)
    result = await searcher.search("ceo", limit=10)

    assert len(result) == 1
    assert result[0].telegram_username == "testuser"
    assert result[0].source == "telegram_search"


@pytest.mark.asyncio
async def test_telegram_public_search_dedup_usernames():
    msg1 = MagicMock()
    msg1.from_user = MagicMock()
    msg1.from_user.id = 1
    msg1.from_user.username = "alice"
    msg1.from_user.first_name = "Alice"
    msg1.from_user.last_name = None

    msg2 = MagicMock()
    msg2.from_user = MagicMock()
    msg2.from_user.id = 2
    msg2.from_user.username = "alice"
    msg2.from_user.first_name = "Alice"
    msg2.from_user.last_name = None

    mock_client = MagicMock()
    mock_client.search_global = AsyncMock(return_value=[msg1, msg2])

    searcher = TelegramPublicSearch(client=mock_client)
    result = await searcher.search("alice", limit=10)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# ChannelMembersParser
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_channel_parser_no_pyrogram():
    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", False):
        parser = ChannelMembersParser()
        result = await parser.parse("@testchannel", limit=10)
        assert result == []


@pytest.mark.asyncio
async def test_channel_parser_keyword_filter():
    user1 = MagicMock()
    user1.id = 1
    user1.username = "ceo_user"
    user1.first_name = "John"
    user1.last_name = "Doe"
    user1.bio = "CEO"

    user2 = MagicMock()
    user2.id = 2
    user2.username = "random_user"
    user2.first_name = "Jane"
    user2.last_name = "Doe"
    user2.bio = "Designer"

    member1 = MagicMock()
    member1.user = user1
    member2 = MagicMock()
    member2.user = user2

    async def async_generator():
        for m in [member1, member2]:
            yield m

    mock_client = MagicMock()
    mock_client.get_chat_members = MagicMock(return_value=async_generator())

    parser = ChannelMembersParser(client=mock_client)
    result = await parser.parse("@testchannel", limit=10, keywords=["CEO"])

    assert len(result) == 1
    assert result[0].telegram_username == "ceo_user"


# ---------------------------------------------------------------------------
# enrich_contact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_contact_no_pyrogram():
    contact = DiscoveredContact(telegram_username="test")
    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", False):
        result = await enrich_contact(contact)
    assert result.first_name is None


@pytest.mark.asyncio
async def test_enrich_contact_fills_fields(mock_pyrogram_user):
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(return_value=[mock_pyrogram_user])

    contact = DiscoveredContact(telegram_username="testuser")
    result = await enrich_contact(contact, client=mock_client)

    assert result.telegram_user_id == 123456
    assert result.first_name == "Test"
    assert result.last_name == "User"


# ---------------------------------------------------------------------------
# discover_leads dispatcher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_leads_unknown_source():
    result = await discover_leads(LeadCriteria(query="x"), source="unknown")
    assert result == []
