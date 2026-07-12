"""Tests for lead discovery adapters."""

import asyncio
import importlib

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.lead_discovery as lead_discovery
from app.services.lead_discovery import (
    ChannelMembersParser,
    DiscoveredContact,
    GenericJSONAdapter,
    LeadCriteria,
    RosprofileAdapter,
    TelegramPublicSearch,
    discover_leads,
    enrich_contact,
    _iter_search_items,
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
def mock_deleted_user():
    user = MagicMock()
    user.id = 999
    user.username = "deleted"
    user.first_name = "Deleted"
    user.last_name = "User"
    user.is_deleted = True
    user.bio = None
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
async def test_generic_json_adapter_parses_list_response_and_optional_params():
    adapter = GenericJSONAdapter(api_url="http://example.com/api", api_key="")
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "username": "jane_doe",
            "user_id": 42,
            "company_name": "Globex",
            "position": "Founder",
        },
        "bad item",
    ]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await adapter.search(
            LeadCriteria(query="founder", limit=5, job_title="CEO", company="Globex")
        )

    assert len(result) == 1
    assert result[0].telegram_username == "jane_doe"
    assert result[0].telegram_user_id == 42
    assert result[0].company_name == "Globex"
    params = mock_client.get.call_args.kwargs["params"]
    assert params["job_title"] == "CEO"
    assert params["company"] == "Globex"


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


@pytest.mark.asyncio
async def test_rosprofile_adapter_requires_configured_url():
    adapter = RosprofileAdapter(api_url="")

    with pytest.raises(NotImplementedError, match="Rosprofile integration requires"):
        await adapter.search(LeadCriteria(query="ceo"))


@pytest.mark.asyncio
async def test_rosprofile_adapter_delegates_to_generic_search():
    adapter = RosprofileAdapter(api_url="http://rosprofile.test/api")
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": [{"username": "lead"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await adapter.search(LeadCriteria(query="ceo"))

    assert result[0].telegram_username == "lead"


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
async def test_telegram_public_search_supports_q_argument_fallback(mock_pyrogram_message):
    def search_global(*, q=None, limit=None):
        assert q == "ceo"
        assert limit == 10
        return [mock_pyrogram_message]

    mock_client = MagicMock()
    mock_client.search_global = search_global

    result = await TelegramPublicSearch(client=mock_client).search("ceo", limit=10)

    assert result[0].telegram_username == "testuser"


@pytest.mark.asyncio
async def test_telegram_public_search_accepts_direct_user_items(
    mock_pyrogram_user, monkeypatch
):
    class DummyUser:
        pass

    dummy = DummyUser()
    dummy.id = mock_pyrogram_user.id
    dummy.username = mock_pyrogram_user.username
    dummy.first_name = mock_pyrogram_user.first_name
    dummy.last_name = mock_pyrogram_user.last_name

    monkeypatch.setattr("app.services.lead_discovery.User", DummyUser)
    mock_client = MagicMock()
    mock_client.search_global = MagicMock(return_value=[dummy])

    result = await TelegramPublicSearch(client=mock_client).search("ceo", limit=10)

    assert result[0].telegram_username == "testuser"


@pytest.mark.asyncio
async def test_telegram_public_search_uses_user_attribute_and_skips_invalid_items(
    mock_pyrogram_user,
):
    item_with_user = MagicMock()
    item_with_user.from_user = None
    item_with_user.user = mock_pyrogram_user
    item_without_user = MagicMock()
    item_without_user.from_user = None
    item_without_user.user = None
    user_without_username = MagicMock()
    user_without_username.username = None
    item_without_username = MagicMock()
    item_without_username.from_user = user_without_username

    mock_client = MagicMock()
    mock_client.search_global = AsyncMock(
        return_value=[item_without_user, item_without_username, item_with_user]
    )

    searcher = TelegramPublicSearch(client=mock_client)
    result = await searcher.search("ceo", limit=10)

    assert len(result) == 1
    assert result[0].telegram_username == "testuser"


@pytest.mark.asyncio
async def test_telegram_public_search_returns_empty_when_no_client_or_session(
    monkeypatch,
):
    monkeypatch.delenv("TELEGRAM_DISCOVERY_SESSION_STRING", raising=False)
    monkeypatch.delenv("TELEGRAM_SESSION_STRING", raising=False)

    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_discovery.get_settings") as mock_settings:
            mock_settings.return_value.telegram_api_id = 12345
            mock_settings.return_value.telegram_api_hash = "hash"

            result = await TelegramPublicSearch().search("ceo")

    assert result == []


@pytest.mark.asyncio
async def test_telegram_public_search_temporary_client_is_stopped(
    mock_pyrogram_message, monkeypatch
):
    monkeypatch.setenv("TELEGRAM_DISCOVERY_SESSION_STRING", "session")
    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_discovery.Client") as MockClient:
            client = MockClient.return_value
            client.start = AsyncMock()
            client.stop = AsyncMock()
            client.search_global = AsyncMock(return_value=[mock_pyrogram_message])

            with patch("app.services.lead_discovery.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "hash"

                result = await TelegramPublicSearch().search("ceo")

    assert len(result) == 1
    client.start.assert_awaited_once()
    client.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_public_search_handles_search_and_stop_errors(monkeypatch):
    monkeypatch.setenv("TELEGRAM_DISCOVERY_SESSION_STRING", "session")
    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_discovery.Client") as MockClient:
            client = MockClient.return_value
            client.start = AsyncMock()
            client.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
            client.search_global = AsyncMock(side_effect=RuntimeError("search failed"))

            with patch("app.services.lead_discovery.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "hash"

                result = await TelegramPublicSearch().search("ceo")

    assert result == []
    client.stop.assert_awaited_once()


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


@pytest.mark.asyncio
async def test_telegram_public_search_stops_at_limit():
    messages = []
    for user_id, username in [(1, "alice"), (2, "bob")]:
        msg = MagicMock()
        msg.from_user = MagicMock()
        msg.from_user.id = user_id
        msg.from_user.username = username
        msg.from_user.first_name = username.title()
        msg.from_user.last_name = None
        messages.append(msg)

    mock_client = MagicMock()
    mock_client.search_global = MagicMock(return_value=messages)

    result = await TelegramPublicSearch(client=mock_client).search("lead", limit=1)

    assert [item.telegram_username for item in result] == ["alice"]


@pytest.mark.asyncio
async def test_iter_search_items_supports_none_async_iterable_and_single_object():
    assert [item async for item in _iter_search_items(None)] == []

    async def async_items():
        yield "a"
        yield "b"

    assert [item async for item in _iter_search_items(async_items())] == ["a", "b"]
    assert [item async for item in _iter_search_items({"not": "iterated"})] == [
        {"not": "iterated"}
    ]


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
async def test_channel_parser_returns_empty_without_client_or_session(monkeypatch):
    monkeypatch.delenv("TELEGRAM_DISCOVERY_SESSION_STRING", raising=False)
    monkeypatch.delenv("TELEGRAM_SESSION_STRING", raising=False)

    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_discovery.get_settings") as mock_settings:
            mock_settings.return_value.telegram_api_id = 12345
            mock_settings.return_value.telegram_api_hash = "hash"

            result = await ChannelMembersParser().parse("@channel")

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


@pytest.mark.asyncio
async def test_channel_parser_deduplicates_and_respects_limit(mock_pyrogram_user):
    member = MagicMock(user=mock_pyrogram_user)

    async def async_generator():
        for _ in range(3):
            yield member

    mock_client = MagicMock()
    mock_client.get_chat_members = MagicMock(return_value=async_generator())

    result = await ChannelMembersParser(client=mock_client).parse("@channel", limit=1)

    assert len(result) == 1
    assert result[0].telegram_username == "testuser"


@pytest.mark.asyncio
async def test_channel_parser_skips_members_without_visible_usernames(mock_pyrogram_user):
    no_user = MagicMock(user=None)
    no_username = MagicMock()
    no_username.user = MagicMock()
    no_username.user.username = None
    duplicate = MagicMock(user=mock_pyrogram_user)

    async def async_generator():
        for member in [no_user, no_username, duplicate, duplicate]:
            yield member

    mock_client = MagicMock()
    mock_client.get_chat_members = MagicMock(return_value=async_generator())

    result = await ChannelMembersParser(client=mock_client).parse("@channel", limit=5)

    assert len(result) == 1
    assert result[0].telegram_username == "testuser"


@pytest.mark.asyncio
async def test_channel_parser_handles_fetch_error():
    mock_client = MagicMock()
    mock_client.get_chat_members = MagicMock(side_effect=RuntimeError("boom"))

    result = await ChannelMembersParser(client=mock_client).parse("@channel")

    assert result == []


@pytest.mark.asyncio
async def test_channel_parser_temporary_client_stop_failure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_DISCOVERY_SESSION_STRING", "session")

    async def async_generator():
        if False:
            yield None

    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_discovery.Client") as MockClient:
            client = MockClient.return_value
            client.start = AsyncMock()
            client.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
            client.get_chat_members = MagicMock(return_value=async_generator())

            with patch("app.services.lead_discovery.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "hash"

                result = await ChannelMembersParser().parse("@channel")

    assert result == []
    client.start.assert_awaited_once()
    client.stop.assert_awaited_once()


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


@pytest.mark.asyncio
async def test_enrich_contact_returns_original_without_username():
    contact = DiscoveredContact(first_name="Known")

    result = await enrich_contact(contact)

    assert result is contact
    assert result.first_name == "Known"


@pytest.mark.asyncio
async def test_enrich_contact_returns_original_without_client_or_session(monkeypatch):
    monkeypatch.delenv("TELEGRAM_DISCOVERY_SESSION_STRING", raising=False)
    monkeypatch.delenv("TELEGRAM_SESSION_STRING", raising=False)
    contact = DiscoveredContact(telegram_username="known")

    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_discovery.get_settings") as mock_settings:
            mock_settings.return_value.telegram_api_id = 12345
            mock_settings.return_value.telegram_api_hash = "hash"

            result = await enrich_contact(contact)

    assert result is contact


@pytest.mark.asyncio
async def test_enrich_contact_skips_deleted_user_and_handles_lookup_error(
    mock_deleted_user,
):
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(return_value=[mock_deleted_user])
    contact = DiscoveredContact(telegram_username="deleted", first_name="Original")

    result = await enrich_contact(contact, client=mock_client)

    assert result.first_name == "Original"

    mock_client.get_users = AsyncMock(side_effect=RuntimeError("lookup failed"))
    assert await enrich_contact(contact, client=mock_client) is contact


@pytest.mark.asyncio
async def test_enrich_contact_temporary_client_stop_failure(
    mock_pyrogram_user, monkeypatch
):
    monkeypatch.setenv("TELEGRAM_DISCOVERY_SESSION_STRING", "session")
    with patch("app.services.lead_discovery._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_discovery.Client") as MockClient:
            client = MockClient.return_value
            client.start = AsyncMock()
            client.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
            client.get_users = AsyncMock(return_value=[mock_pyrogram_user])

            with patch("app.services.lead_discovery.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "hash"

                contact = DiscoveredContact(telegram_username="testuser")
                result = await enrich_contact(contact)

    assert result.telegram_user_id == 123456
    client.stop.assert_awaited_once()


# ---------------------------------------------------------------------------
# discover_leads dispatcher
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_leads_dispatches_supported_sources(monkeypatch):
    criteria = LeadCriteria(query="crm", limit=3, keywords=["ceo"])
    expected = [DiscoveredContact(telegram_username="lead")]

    async def fake_search(self, query, limit):
        assert query == "crm"
        assert limit == 3
        return expected

    async def fake_parse(self, channel_username, limit, keywords):
        assert channel_username == "crm"
        assert limit == 3
        assert keywords == ["ceo"]
        return expected

    async def fake_external(self, incoming_criteria):
        assert incoming_criteria is criteria
        return expected

    monkeypatch.setattr(TelegramPublicSearch, "search", fake_search)
    assert await discover_leads(criteria, source="telegram_search") is expected

    monkeypatch.setattr(ChannelMembersParser, "parse", fake_parse)
    assert await discover_leads(criteria, source="channel_parse") is expected

    monkeypatch.setattr(GenericJSONAdapter, "search", fake_external)
    assert await discover_leads(criteria, source="external_api") is expected


@pytest.mark.asyncio
async def test_discover_leads_unknown_source():
    result = await discover_leads(LeadCriteria(query="x"), source="unknown")
    assert result == []


def test_import_sets_event_loop_when_missing():
    loop = asyncio.new_event_loop()
    try:
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            with patch("asyncio.new_event_loop", return_value=loop) as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    importlib.reload(lead_discovery)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(loop)
    finally:
        importlib.reload(lead_discovery)
        loop.close()
