"""Tests for daily reset and cooldown recovery scheduler jobs."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.scheduler import CampaignScheduler
from app.models.telegram_account import TelegramAccount


@pytest.mark.asyncio
async def test_scheduler_adds_reset_job():
    scheduler = CampaignScheduler()
    with patch.object(scheduler._scheduler, "add_job") as mock_add_job:
        with patch.object(scheduler._scheduler, "start"):
            scheduler.start()

    job_ids = {call.kwargs.get("id") or call.args[3] for call in mock_add_job.call_args_list}
    assert "reset_daily_counters" in job_ids
    assert "recover_cooldown_accounts" in job_ids
    assert "auto_close_conversations" in job_ids


@pytest.mark.asyncio
async def test_reset_daily_counters_job_executes_update(mock_db):
    scheduler = CampaignScheduler()
    with patch("app.core.scheduler.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        await scheduler._run_reset_daily_counters()

    # The job should execute an update statement via the session
    assert mock_db.execute.called
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_recover_cooldown_accounts_job_executes_update(mock_db):
    scheduler = CampaignScheduler()
    with patch("app.core.scheduler.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        await scheduler._run_recover_cooldown_accounts()

    assert mock_db.execute.called
    mock_db.commit.assert_awaited()
