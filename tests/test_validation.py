"""Tests for Telegram username validation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.lead_validation import validate_telegram_usernames, validate_and_enrich


@pytest.fixture
def mock_pyrogram_user():
    user = MagicMock()
    user.id = 123456
    user.username = "valid_user"
    user.first_name = "Valid"
    user.last_name = "User"
    user.is_deleted = False
    return user


@pytest.fixture
def mock_deleted_user():
    user = MagicMock()
    user.id = 999
    user.username = "deleted_user"
    user.first_name = "Deleted"
    user.last_name = "User"
    user.is_deleted = True
    return user


@pytest.mark.asyncio
async def test_validate_no_pyrogram():
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", False):
        result = await validate_telegram_usernames(["user1"])
        assert result == []


@pytest.mark.asyncio
async def test_validate_empty_list():
    result = await validate_telegram_usernames([])
    assert result == []


@pytest.mark.asyncio
async def test_validate_filters_deleted_users(mock_pyrogram_user, mock_deleted_user):
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(return_value=[mock_pyrogram_user, mock_deleted_user])

    result = await validate_telegram_usernames(
        ["valid_user", "deleted_user"], client=mock_client
    )
    assert result == ["valid_user"]


@pytest.mark.asyncio
async def test_validate_batch_processing():
    users = []
    for i in range(250):
        u = MagicMock()
        u.id = i
        u.username = f"user_{i}"
        u.is_deleted = False
        users.append(u)

    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(return_value=users[:200])

    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        result = await validate_telegram_usernames(
            [f"user_{i}" for i in range(250)], client=mock_client
        )

    # get_users should be called twice (batches of 200)
    assert mock_client.get_users.call_count == 2


@pytest.mark.asyncio
async def test_validate_and_enrich_returns_info(mock_pyrogram_user):
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(return_value=[mock_pyrogram_user])

    result = await validate_and_enrich(["valid_user"], client=mock_client)
    assert "valid_user" in result
    assert result["valid_user"]["user_id"] == 123456
    assert result["valid_user"]["first_name"] == "Valid"


@pytest.mark.asyncio
async def test_validate_and_enrich_skips_deleted(mock_deleted_user):
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(return_value=[mock_deleted_user])

    result = await validate_and_enrich(["deleted_user"], client=mock_client)
    assert "deleted_user" not in result
