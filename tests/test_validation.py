"""Tests for Telegram username validation."""

import asyncio
import importlib

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.lead_validation as lead_validation
from app.services.lead_validation import validate_and_enrich, validate_telegram_usernames


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
async def test_validate_returns_empty_when_no_client_and_no_settings():
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_validation.get_settings") as mock_settings:
            mock_settings.return_value.telegram_api_id = None
            mock_settings.return_value.telegram_api_hash = None

            result = await validate_telegram_usernames(["user1"])

    assert result == []


@pytest.mark.asyncio
async def test_validate_filters_deleted_users(mock_pyrogram_user, mock_deleted_user):
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(
        return_value=[mock_pyrogram_user, mock_deleted_user]
    )

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
        await validate_telegram_usernames(
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
    assert result["valid_user"]["is_valid"] == "valid"


@pytest.mark.asyncio
async def test_validate_and_enrich_skips_deleted(mock_deleted_user):
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(return_value=[mock_deleted_user])

    result = await validate_and_enrich(["deleted_user"], client=mock_client)
    assert "deleted_user" not in result


@pytest.mark.asyncio
async def test_validate_creates_temp_client_when_needed():
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_validation.Client") as MockClient:
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.stop = AsyncMock()
            client_inst.get_users = AsyncMock(return_value=[])

            with patch("app.services.lead_validation.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "abc"

                result = await validate_telegram_usernames(["user1"])
                assert result == []
                MockClient.assert_called_once()
                client_inst.start.assert_awaited_once()
                client_inst.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_logs_when_temp_client_stop_fails():
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_validation.Client") as MockClient:
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
            client_inst.get_users = AsyncMock(return_value=[])

            with patch("app.services.lead_validation.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "abc"

                result = await validate_telegram_usernames(["user1"])

    assert result == []
    client_inst.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_handles_batch_exception():
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(side_effect=Exception("API error"))

    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        result = await validate_telegram_usernames(["user1"], client=mock_client)
    assert result == []


@pytest.mark.asyncio
async def test_validate_handles_outer_iteration_exception():
    class BrokenUsernames:
        def __bool__(self):
            return True

        def __len__(self):
            raise RuntimeError("length failed")

    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        result = await validate_telegram_usernames(
            BrokenUsernames(), client=MagicMock()
        )

    assert result == []


@pytest.mark.asyncio
async def test_validate_and_enrich_no_pyrogram_or_empty_usernames():
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", False):
        assert await validate_and_enrich(["user1"]) == {}
    assert await validate_and_enrich([]) == {}


@pytest.mark.asyncio
async def test_validate_and_enrich_returns_empty_without_client_or_settings():
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_validation.get_settings") as mock_settings:
            mock_settings.return_value.telegram_api_id = None
            mock_settings.return_value.telegram_api_hash = None

            result = await validate_and_enrich(["user1"])

    assert result == {}


@pytest.mark.asyncio
async def test_validate_and_enrich_creates_temp_client(mock_pyrogram_user):
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_validation.Client") as MockClient:
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.stop = AsyncMock()
            client_inst.get_users = AsyncMock(return_value=[mock_pyrogram_user])

            with patch("app.services.lead_validation.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "abc"

                result = await validate_and_enrich(["valid_user"])

    assert result["valid_user"]["user_id"] == 123456
    client_inst.start.assert_awaited_once()
    client_inst.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_and_enrich_handles_batch_exception():
    mock_client = MagicMock()
    mock_client.get_users = AsyncMock(side_effect=Exception("API error"))

    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        result = await validate_and_enrich(["user1"], client=mock_client)

    assert result == {}


@pytest.mark.asyncio
async def test_validate_and_enrich_handles_outer_iteration_exception():
    class BrokenUsernames:
        def __bool__(self):
            return True

        def __len__(self):
            raise RuntimeError("length failed")

    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        result = await validate_and_enrich(BrokenUsernames(), client=MagicMock())

    assert result == {}


@pytest.mark.asyncio
async def test_validate_and_enrich_logs_when_temp_client_stop_fails(mock_pyrogram_user):
    with patch("app.services.lead_validation._PYROGRAM_AVAILABLE", True):
        with patch("app.services.lead_validation.Client") as MockClient:
            client_inst = MockClient.return_value
            client_inst.start = AsyncMock()
            client_inst.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
            client_inst.get_users = AsyncMock(return_value=[mock_pyrogram_user])

            with patch("app.services.lead_validation.get_settings") as mock_settings:
                mock_settings.return_value.telegram_api_id = 12345
                mock_settings.return_value.telegram_api_hash = "abc"

                result = await validate_and_enrich(["valid_user"])

    assert "valid_user" in result
    client_inst.stop.assert_awaited_once()


def test_import_sets_event_loop_when_missing():
    loop = asyncio.new_event_loop()
    try:
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            with patch("asyncio.new_event_loop", return_value=loop) as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    importlib.reload(lead_validation)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(loop)
    finally:
        importlib.reload(lead_validation)
        loop.close()
