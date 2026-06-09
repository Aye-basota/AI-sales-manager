"""Tests for timezone-aware working hours."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.core.scheduler import is_within_working_hours


def test_within_hours_moscow():
    # 12:00 MSK on a weekday
    now = datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    assert is_within_working_hours(
        "Europe/Moscow", time(9, 0), time(18, 0), now
    ) is True


def test_after_hours_moscow_from_utc():
    # 20:00 UTC = 23:00 MSK (still within working hours)
    # Use 22:00 UTC = 01:00 MSK next day (outside working hours)
    now = datetime(2024, 1, 15, 22, 0, tzinfo=ZoneInfo("UTC"))
    assert is_within_working_hours(
        "Europe/Moscow", time(9, 0), time(18, 0), now
    ) is False


def test_before_hours_moscow():
    now = datetime(2024, 1, 15, 7, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    assert is_within_working_hours(
        "Europe/Moscow", time(9, 0), time(18, 0), now
    ) is False


def test_invalid_timezone_defaults_to_utc():
    now = datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("UTC"))
    assert is_within_working_hours(
        "NotA/Timezone", time(9, 0), time(18, 0), now
    ) is True


def test_naive_datetime_localized():
    # Naive datetime should be treated as if it is in the target timezone
    now = datetime(2024, 1, 15, 12, 0)
    assert is_within_working_hours(
        "Europe/Moscow", time(9, 0), time(18, 0), now
    ) is True
