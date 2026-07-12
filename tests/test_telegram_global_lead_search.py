"""Tests for Telegram MTProto global lead discovery."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.telegram_global_lead_search import (
    TelegramGlobalLeadSearch,
    TelegramGlobalSearchCriteria,
    _chat_group_record,
    _chat_title,
    _contact_record_from_message,
    _format_date,
    _is_public_group_like_message,
    _is_recent_message,
    _iterate_result_items,
    _message_link,
    build_telegram_global_queries,
    normalize_country,
    normalize_language,
)


def _message(
    text: str,
    *,
    user_id: int = 123,
    username: str | None = "leaduser",
    chat_username: str | None = "logistics_chat",
    chat_type: str = "supergroup",
):
    user = SimpleNamespace(
        id=user_id,
        username=username,
        first_name="Lead",
        last_name="User",
        is_bot=False,
        is_deleted=False,
    )
    chat = SimpleNamespace(
        id=-100123,
        username=chat_username,
        title="Logistics founders",
        type=SimpleNamespace(value=chat_type),
    )
    return SimpleNamespace(
        id=42,
        text=text,
        caption=None,
        from_user=user,
        chat=chat,
        date=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )


def test_normalizes_country_and_language_names():
    assert normalize_country("Польша") == "pl"
    assert normalize_country("Poland") == "pl"
    assert normalize_language("польский") == "pl"
    assert normalize_language("English") == "en"
    assert normalize_country("") == ""


def test_builds_local_and_english_queries():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM for logistics companies",
        audience_description="Владельцы и директора логистических компаний",
        country="Польша",
        language="польский",
        pain_keywords="ищем CRM, автоматизация склада, нужен IT-подрядчик",
    )

    queries = build_telegram_global_queries(criteria)

    assert "logistyka" in queries
    assert "spedycja" in queries
    assert "freight forwarding" in queries
    assert any("CRM Poland".lower() == query.lower() for query in queries)
    assert len(queries) == len({query.lower() for query in queries})


def test_build_queries_without_country_and_short_terms():
    criteria = TelegramGlobalSearchCriteria(
        business_description="AI",
        audience_description="AI",
        country="",
        language="English",
        pain_keywords="",
    )

    queries = build_telegram_global_queries(criteria)

    assert "AI" not in queries
    assert "CRM" in queries
    assert "contractor" in queries


def test_polish_logistics_expansions_are_only_for_polish_market():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM and automation",
        audience_description="logistics companies",
        country="Russia",
        language="Russian",
        pain_keywords="нужен CRM",
    )

    queries = build_telegram_global_queries(criteria)

    assert "logistyka" not in queries
    assert "spedycja" not in queries
    assert any("CRM Russia".lower() == query.lower() for query in queries)


def test_message_helper_edge_cases():
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    assert _format_date(now) == now.isoformat()
    assert _format_date(0).startswith("1970-01-01T00:00:00+00:00")
    assert _format_date(None) == ""

    assert _is_recent_message(SimpleNamespace(date="not datetime"), 30) is True
    assert (
        _is_recent_message(
            SimpleNamespace(date=datetime.now() - timedelta(days=1)), 30
        )
        is True
    )

    assert _message_link(SimpleNamespace(chat=SimpleNamespace(username=None), id=1)) == ""
    assert _chat_title(SimpleNamespace(title=None, username="group", first_name=None)) == "group"
    assert _chat_title(SimpleNamespace(title=None, username=None, first_name="Lead")) == "Lead"
    assert _chat_group_record(SimpleNamespace(id=1, title="Group", username="g", type="supergroup")) == {
        "id": 1,
        "title": "Group",
        "username": "g",
        "type": "supergroup",
    }


def test_public_group_filter_rejects_missing_private_bots_and_deleted_users():
    assert _is_public_group_like_message(SimpleNamespace(chat=None, from_user=None)) is False
    assert (
        _is_public_group_like_message(
            _message("need CRM", chat_type="private")
        )
        is False
    )
    bot_message = _message("need CRM")
    bot_message.from_user.is_bot = True
    assert _is_public_group_like_message(bot_message) is False
    deleted_message = _message("need CRM")
    deleted_message.from_user.is_deleted = True
    assert _is_public_group_like_message(deleted_message) is False


def test_contact_record_requires_visible_author_identity():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM",
        audience_description="cafes",
        country="Russia",
        language="Russian",
    )
    assert _contact_record_from_message(SimpleNamespace(from_user=None), criteria) is None

    message = _message("need CRM", user_id=None, username=None)

    assert _contact_record_from_message(message, criteria) is None


@pytest.mark.asyncio
async def test_iterate_result_items_supports_none_async_iterable_and_single_object():
    assert [item async for item in _iterate_result_items(None)] == []

    async def async_items():
        yield "one"
        yield "two"

    assert [item async for item in _iterate_result_items(async_items())] == [
        "one",
        "two",
    ]
    assert [item async for item in _iterate_result_items({"raw": "object"})] == [
        {"raw": "object"}
    ]


@pytest.mark.asyncio
async def test_global_search_collects_visible_authors_from_async_generator():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM",
        audience_description="logistics companies",
        country="Poland",
        language="English",
        pain_keywords="looking for CRM",
        limit=1,
        messages_per_query=5,
    )

    async def search_global(**kwargs):
        assert "query" in kwargs
        yield _message("Looking for CRM for a transport company")

    client = MagicMock()
    client.search_global = search_global

    result = await TelegramGlobalLeadSearch().run(criteria, telegram_client=client)

    assert result.posts_checked == 1
    assert len(result.records) == 1
    record = result.records[0]
    assert record["telegram_user_id"] == 123
    assert record["telegram_username"] == "leaduser"
    assert record["source"] == "telegram_search"
    assert record["source_url"] == "https://t.me/logistics_chat/42"
    assert "CRM" in record["source_summary"]
    assert len(result.groups) == 1


@pytest.mark.asyncio
async def test_global_search_filters_ads_private_chats_and_duplicates():
    criteria = TelegramGlobalSearchCriteria(
        business_description="ERP",
        audience_description="transport business",
        country="Poland",
        language="English",
        pain_keywords="need ERP",
        limit=5,
        messages_per_query=10,
    )

    async def search_global(**kwargs):
        yield _message("job hiring transport manager")
        yield _message("need ERP for warehouse", chat_type="private")
        yield _message("need ERP for warehouse", user_id=1, username="alice")
        yield _message("need ERP for warehouse", user_id=1, username="alice")

    client = MagicMock()
    client.search_global = search_global

    result = await TelegramGlobalLeadSearch().run(criteria, telegram_client=client)

    assert len(result.records) == 1
    assert result.records[0]["telegram_username"] == "alice"


@pytest.mark.asyncio
async def test_global_search_supports_awaitable_list_mocks():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM",
        audience_description="cafes",
        country="Russia",
        language="Russian",
        pain_keywords="нужен CRM",
        limit=1,
    )

    async def search_global(**kwargs):
        return [_message("нужен CRM для кофейни")]

    client = MagicMock()
    client.search_global = search_global

    result = await TelegramGlobalLeadSearch().run(criteria, telegram_client=client)

    assert len(result.records) == 1


@pytest.mark.asyncio
async def test_global_search_supports_q_argument_fallback():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM",
        audience_description="cafes",
        country="Russia",
        language="Russian",
        pain_keywords="нужен CRM",
        limit=1,
        messages_per_query=3,
    )

    def search_global(*, q=None, limit=None):
        assert q
        assert limit == 3
        return [_message("нужен CRM для кофейни")]

    client = MagicMock()
    client.search_global = search_global

    result = await TelegramGlobalLeadSearch().run(criteria, telegram_client=client)

    assert len(result.records) == 1


@pytest.mark.asyncio
async def test_global_search_skips_empty_old_and_anonymous_messages():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM",
        audience_description="cafes",
        country="Russia",
        language="Russian",
        pain_keywords="нужен CRM",
        limit=5,
        messages_per_query=5,
    )
    empty = _message("")
    old = _message("нужен CRM для кофейни")
    old.date = datetime.now(timezone.utc) - timedelta(days=60)
    anonymous = _message("нужен CRM для кофейни", user_id=None, username=None)

    async def search_global(**kwargs):
        for item in [empty, old, anonymous]:
            yield item

    client = MagicMock()
    client.search_global = search_global

    result = await TelegramGlobalLeadSearch().run(criteria, telegram_client=client)

    assert result.records == []
    assert result.posts_checked == len(result.queries) * 3


@pytest.mark.asyncio
async def test_global_search_breaks_inside_query_after_limit_is_reached():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM",
        audience_description="cafes",
        country="Russia",
        language="Russian",
        pain_keywords="нужен CRM",
        limit=1,
        messages_per_query=5,
    )

    async def search_global(**kwargs):
        yield _message("нужен CRM для кофейни", user_id=1, username="alice")
        yield _message("нужен CRM для кофейни", user_id=2, username="bob")

    client = MagicMock()
    client.search_global = search_global

    result = await TelegramGlobalLeadSearch().run(criteria, telegram_client=client)

    assert [record["telegram_username"] for record in result.records] == ["alice"]
    assert result.posts_checked == 2


@pytest.mark.asyncio
async def test_global_search_records_query_errors():
    criteria = TelegramGlobalSearchCriteria(
        business_description="CRM",
        audience_description="cafes",
        country="Russia",
        language="Russian",
        pain_keywords="нужен CRM",
        limit=1,
    )

    def search_global(**kwargs):
        raise RuntimeError("telegram down")

    client = MagicMock()
    client.search_global = search_global

    result = await TelegramGlobalLeadSearch().run(criteria, telegram_client=client)

    assert result.records == []
    assert result.errors
    assert "telegram down" in result.errors[0]
