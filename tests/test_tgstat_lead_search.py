"""Tests for TGStat-based lead discovery helpers."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.bots.admin_bot import _discovery_csv_bytes
from app.services.tgstat_lead_search import (
    TGStatLeadSearch,
    TgstatLeadSearchCriteria,
    build_tgstat_queries,
    normalize_country,
    normalize_language,
)


def test_normalizes_country_and_language_names():
    assert normalize_country("Польша") == "pl"
    assert normalize_country("Poland") == "pl"
    assert normalize_language("польский") == "pl"
    assert normalize_language("English") == "en"


def test_builds_queries_from_audience_country_and_pains():
    criteria = TgstatLeadSearchCriteria(
        business_description="CRM for logistics companies",
        audience_description="Владельцы и директора логистических компаний",
        country="Польша",
        language="польский",
        pain_keywords="ищем CRM, автоматизация склада, нужен IT-подрядчик",
    )

    queries = build_tgstat_queries(criteria)

    assert "logistyka" in queries
    assert "spedycja" in queries
    assert "freight forwarding" in queries
    assert any("логист" in query.lower() for query in queries)
    assert any("CRM Poland".lower() == query.lower() for query in queries)
    assert len(queries) == len({query.lower() for query in queries})


def test_csv_contains_upload_columns_and_source_context():
    record = {
        "telegram_user_id": 123,
        "telegram_username": "lead",
        "first_name": "Lead",
        "source_url": "https://t.me/group/10",
        "source_summary": "Asked for CRM",
        "source_message_text": "Can anyone recommend CRM?",
        "source_message_date": "2026-07-10T10:00:00+00:00",
        "source": "tgstat",
        "last_source": "tgstat",
        "is_valid": "unknown",
    }

    csv_text = _discovery_csv_bytes([record]).decode("utf-8-sig")

    assert "telegram_user_id" in csv_text
    assert "source_summary" in csv_text
    assert "Asked for CRM" in csv_text


@pytest.mark.asyncio
async def test_record_from_tgstat_post_resolves_visible_author():
    criteria = TgstatLeadSearchCriteria(
        business_description="CRM",
        audience_description="logistics companies",
        country="Poland",
        language="Polish",
        pain_keywords="CRM",
    )
    searcher = TGStatLeadSearch(token="token")

    async def fake_get_messages(chat_username, message_id):
        assert chat_username == "logistics_chat"
        assert message_id == 42
        return SimpleNamespace(
            text="Looking for CRM for a transport company",
            from_user=SimpleNamespace(
                id=123,
                username="leaduser",
                first_name="Lead",
                last_name="User",
            ),
            chat=SimpleNamespace(title="Logistics chat"),
            date=datetime(2026, 7, 10, tzinfo=timezone.utc),
        )

    client = SimpleNamespace(get_messages=fake_get_messages)
    post = {"link": "https://t.me/logistics_chat/42", "text": "Looking for CRM"}

    record = await searcher._record_from_tgstat_post(post, criteria, client)

    assert record["telegram_user_id"] == 123
    assert record["telegram_username"] == "leaduser"
    assert record["source_url"] == "https://t.me/logistics_chat/42"
    assert "CRM" in record["source_summary"]
