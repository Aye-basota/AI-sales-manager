"""Tests for contact import helpers."""

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.models.contact import Contact
from app.services.contact_import import (
    _process_dataframe,
    contacts_in_record_order,
    parse_csv,
    parse_excel,
    upsert_contacts,
)
from tests.conftest import MockResult


class TestParseCsv:
    def test_valid_csv_returns_records(self):
        csv_bytes = b"first_name,last_name,phone,telegram_user_id\nAlice,Smith,+123,111\nBob,Jones,+456,222"
        result = parse_csv(csv_bytes)
        assert len(result) == 2
        assert result[0]["first_name"] == "Alice"
        assert result[1]["last_name"] == "Jones"
        assert result[0]["telegram_user_id"] == 111

    def test_invalid_columns_raises_value_error(self):
        csv_bytes = b"first_name,telegram_user_id,email\nAlice,123,alice@test.com"
        with pytest.raises(ValueError, match="Invalid columns"):
            parse_csv(csv_bytes)

    def test_missing_telegram_id_column_raises_value_error(self):
        csv_bytes = b"first_name,last_name,phone\nAlice,Smith,+123"
        with pytest.raises(ValueError, match="telegram_user_id"):
            parse_csv(csv_bytes)

    def test_telegram_id_alias_is_accepted(self):
        csv_bytes = b"first_name,telegram_id\nAlice,123"
        result = parse_csv(csv_bytes)
        assert result[0]["telegram_user_id"] == 123

    def test_telegram_search_source_context_columns_are_accepted(self):
        csv_bytes = (
            "first_name,telegram_user_id,source,source_url,source_summary,"
            "source_message_text,source_message_date,is_valid,icp_score\n"
            "Alice,123,telegram_search,https://t.me/group/10,Asked for CRM,"
            "Can anyone recommend CRM?,2026-07-10T10:00:00+00:00,unknown,82"
        ).encode()

        result = parse_csv(csv_bytes)

        assert result[0]["telegram_user_id"] == 123
        assert result[0]["source"] == "telegram_search"
        assert result[0]["source_url"] == "https://t.me/group/10"
        assert result[0]["source_summary"] == "Asked for CRM"
        assert result[0]["icp_score"] == 82

    def test_empty_csv_returns_empty_list(self):
        csv_bytes = b"first_name,last_name,telegram_user_id\n"
        result = parse_csv(csv_bytes)
        assert result == []

    def test_invalid_numeric_fields_are_ignored(self):
        csv_bytes = (
            b"first_name,telegram_user_id,icp_score\n"
            b"Alice,not-a-number,bad-score"
        )

        result = parse_csv(csv_bytes)

        assert result == [{"first_name": "Alice"}]

    def test_blank_rows_are_skipped(self):
        df = pd.DataFrame({"telegram_user_id": [pd.NA]})

        assert _process_dataframe(df) == []

    def test_parse_csv_value_error_on_pandas_failure(self):
        with patch("app.services.contact_import.pd.read_csv") as mock_read:
            mock_read.side_effect = Exception("bad csv")
            with pytest.raises(ValueError, match="Failed to parse CSV"):
                parse_csv(b"not csv")


class TestParseExcel:
    def test_valid_excel_returns_records(self):
        df = pd.DataFrame(
            {
                "first_name": ["Alice", "Bob"],
                "last_name": ["Smith", "Jones"],
                "phone": ["+123", "+456"],
                "telegram_user_id": ["111", "222"],
            }
        )
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        result = parse_excel(buffer.read())
        assert len(result) == 2
        assert result[0]["first_name"] == "Alice"
        assert result[1]["last_name"] == "Jones"
        assert result[0]["telegram_user_id"] == 111

    def test_invalid_columns_raises_value_error(self):
        df = pd.DataFrame(
            {
                "first_name": ["Alice"],
                "telegram_user_id": ["123"],
                "email": ["alice@test.com"],
            }
        )
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        with pytest.raises(ValueError, match="Invalid columns"):
            parse_excel(buffer.read())

    def test_telegram_id_alias_excel_is_accepted(self):
        df = pd.DataFrame({"first_name": ["Alice"], "telegram_id": ["123"]})
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        result = parse_excel(buffer.read())
        assert result[0]["telegram_user_id"] == 123

    def test_empty_excel_returns_empty_list(self):
        df = pd.DataFrame(columns=["first_name", "last_name", "telegram_user_id"])
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        result = parse_excel(buffer.read())
        assert result == []

    def test_parse_excel_value_error_on_pandas_failure(self):
        with patch("app.services.contact_import.pd.read_excel") as mock_read:
            mock_read.side_effect = Exception("bad excel")
            with pytest.raises(ValueError, match="Failed to parse Excel"):
                parse_excel(b"not excel")


def test_contacts_in_record_order_skips_unknowns_duplicates_and_appends_leftovers():
    first = Contact(telegram_user_id=1, telegram_username="alice", phone="+1")
    second = Contact(telegram_user_id=2, telegram_username="bob", phone="+2")
    leftover = Contact(telegram_user_id=3, telegram_username="carol", phone="+3")
    records = [
        {"telegram_user_id": "not-a-number"},
        {"telegram_user_id": "404"},
        {"telegram_user_id": "1"},
        {"telegram_username": "ALICE"},
        {"phone": "+2"},
    ]

    ordered = contacts_in_record_order(records, [leftover, second, first])

    assert ordered == [first, second, leftover]


@pytest.mark.asyncio
async def test_upsert_contacts_skips_empty_updates_on_existing_contact():
    existing = Contact(
        telegram_username="leaduser",
        first_name="Existing",
        source_summary="Original summary",
    )
    db = AsyncMock()
    db.execute.return_value = MockResult([existing])

    created, updated = await upsert_contacts(
        db,
        [
            {
                "telegram_username": "leaduser",
                "first_name": "",
                "source_summary": "",
                "last_name": "Fresh",
            }
        ],
        source="csv_import",
    )

    assert created == []
    assert updated == [existing]
    assert existing.first_name == "Existing"
    assert existing.source_summary == "Original summary"
    assert existing.last_name == "Fresh"
    assert existing.last_source == "csv_import"
