"""Tests for contact deduplication (upsert) logic."""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock

from app.models.contact import Contact
from app.services.contact_import import upsert_contacts


def _build_mock_session_with_results(results):
    """Build an AsyncMock session that returns *results* from execute()."""
    from unittest.mock import MagicMock
    from tests.conftest import MockResult
    session = AsyncMock()
    session.execute.return_value = MockResult(results)
    session.add = MagicMock()

    async def refresh_side_effect(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid4()
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.now()
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.now()
        if hasattr(obj, 'source') and obj.source is None:
            obj.source = 'csv_import'

    session.refresh.side_effect = refresh_side_effect
    return session


@pytest.mark.asyncio
async def test_upsert_creates_new_contacts(mock_db):
    records = [
        {"telegram_username": "user1", "first_name": "User", "phone": "+111"},
        {"telegram_username": "user2", "first_name": "User2", "phone": "+222"},
    ]
    created, updated = await upsert_contacts(mock_db, records, source="csv_import")
    assert len(created) == 2
    assert len(updated) == 0
    assert created[0].source == "csv_import"
    assert created[0].last_source == "csv_import"


@pytest.mark.asyncio
async def test_upsert_updates_by_username():
    existing = Contact(
        id=uuid4(),
        telegram_username="alice",
        phone="+1234567890",
        first_name="Old",
        last_name="Name",
        source="csv_import",
        last_source="csv_import",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session = _build_mock_session_with_results([existing])

    records = [
        {"telegram_username": "alice", "first_name": "New", "company_name": "NewCorp"},
    ]
    created, updated = await upsert_contacts(session, records, source="telegram_search")

    assert len(created) == 0
    assert len(updated) == 1
    # first_name should NOT be overwritten because it already existed
    assert updated[0].first_name == "Old"
    # company_name was empty, so it should be filled
    assert updated[0].company_name == "NewCorp"
    assert updated[0].last_source == "telegram_search"


@pytest.mark.asyncio
async def test_upsert_updates_by_phone_when_username_missing():
    existing = Contact(
        id=uuid4(),
        telegram_username=None,
        phone="+999",
        first_name="Bob",
        source="csv_import",
        last_source="csv_import",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session = _build_mock_session_with_results([existing])

    records = [
        {"phone": "+999", "last_name": "Marley"},
    ]
    created, updated = await upsert_contacts(session, records, source="external_api")

    assert len(created) == 0
    assert len(updated) == 1
    assert updated[0].last_name == "Marley"
    assert updated[0].last_source == "external_api"


@pytest.mark.asyncio
async def test_upsert_case_insensitive_username():
    existing = Contact(
        id=uuid4(),
        telegram_username="Alice",
        first_name="Alice",
        source="csv_import",
        last_source="csv_import",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session = _build_mock_session_with_results([existing])

    records = [
        {"telegram_username": "alice", "company_name": "Corp"},
    ]
    created, updated = await upsert_contacts(session, records, source="discover")

    assert len(created) == 0
    assert len(updated) == 1
    assert updated[0].company_name == "Corp"


@pytest.mark.asyncio
async def test_upsert_empty_records(mock_db):
    created, updated = await upsert_contacts(mock_db, [], source="csv_import")
    assert created == []
    assert updated == []
