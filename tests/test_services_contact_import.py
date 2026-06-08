"""Tests for contact import helpers."""

from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pytest

from app.services.contact_import import parse_csv, parse_excel


class TestParseCsv:
    def test_valid_csv_returns_records(self):
        csv_bytes = b"first_name,last_name,phone\nAlice,Smith,+123\nBob,Jones,+456"
        result = parse_csv(csv_bytes)
        assert len(result) == 2
        assert result[0]["first_name"] == "Alice"
        assert result[1]["last_name"] == "Jones"

    def test_invalid_columns_raises_value_error(self):
        csv_bytes = b"first_name,email\nAlice,alice@test.com"
        with pytest.raises(ValueError, match="Invalid columns"):
            parse_csv(csv_bytes)

    def test_empty_csv_returns_empty_list(self):
        csv_bytes = b"first_name,last_name\n"
        result = parse_csv(csv_bytes)
        assert result == []


class TestParseExcel:
    def test_valid_excel_returns_records(self):
        df = pd.DataFrame(
            {
                "first_name": ["Alice", "Bob"],
                "last_name": ["Smith", "Jones"],
                "phone": ["+123", "+456"],
            }
        )
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        result = parse_excel(buffer.read())
        assert len(result) == 2
        assert result[0]["first_name"] == "Alice"
        assert result[1]["last_name"] == "Jones"

    def test_invalid_columns_raises_value_error(self):
        df = pd.DataFrame({"first_name": ["Alice"], "email": ["alice@test.com"]})
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        with pytest.raises(ValueError, match="Invalid columns"):
            parse_excel(buffer.read())

    def test_empty_excel_returns_empty_list(self):
        df = pd.DataFrame(columns=["first_name", "last_name"])
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
