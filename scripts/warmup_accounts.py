# Warm-up script for Telegram accounts.
import asyncio
import argparse
import logging
import sys
from uuid import UUID

sys.path.insert(0, ".")

from app.db.session import AsyncSessionLocal
from app.models.telegram_account import TelegramAccount
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def warmup_account(account_id: str) -> None:
    """Mark an account as warming and print honest instructions."""
    try:
        account_uuid = UUID(account_id)
    except ValueError:
        logger.error("Invalid UUID: %s", account_id)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TelegramAccount).where(TelegramAccount.id == account_uuid)
        )
        account = result.scalar_one_or_none()
        if account is None:
            logger.error("Account %s not found in database", account_id)
            return

        account.status = "warming"
        await db.commit()
        logger.info("Account %s status updated to 'warming'", account_id)

    print(
        "Warmup requires manual actions: join 3-5 channels, set avatar and bio, wait 3-7 days. "
        "This script only marks account status."
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Mark Telegram accounts as warming")
    parser.add_argument("--accounts", nargs="+", required=True, help="Account UUIDs")
    args = parser.parse_args()

    for account_id in args.accounts:
        await warmup_account(account_id)


if __name__ == "__main__":
    asyncio.run(main())
