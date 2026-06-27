"""Tests for contact import helpers."""

from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pytest

from app.services.contact_import import parse_csv, parse_excel


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

    def test_empty_csv_returns_empty_list(self):
        csv_bytes = b"first_name,last_name,telegram_user_id\n"
        result = parse_csv(csv_bytes)
        assert result == []


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
