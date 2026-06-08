# Warm-up script for Telegram accounts.
import asyncio
import argparse
import random

from app.bots.seller_client import SellerClient


async def warmup_account(account_id: str, session_string: str, days: int = 7) -> None:
    """Simulate warm-up for a single account."""
    client = SellerClient(account_id=account_id, session_string=session_string)
    await client.start()

    actions = ["subscribe", "set_avatar", "send_message"]
    for day in range(days):
        action = random.choice(actions)
        print(f"Day {day + 1}: {action}")
        if action == "send_message":
            delay = random.randint(1, 5)
            await asyncio.sleep(delay / 10)

    await client.stop()
    print(f"Account {account_id} warm-up completed.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Warm up Telegram accounts")
    parser.add_argument("--accounts", nargs="+", required=True, help="Account IDs")
    parser.add_argument("--days", type=int, default=7, help="Warm-up duration in days")
    args = parser.parse_args()

    for account_id in args.accounts:
        await warmup_account(account_id, f"app_session_{account_id}", args.days)

if __name__ == "__main__":
    asyncio.run(main())
