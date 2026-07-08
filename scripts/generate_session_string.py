"""Generate a Pyrogram Telegram session string.

Run this locally and keep the printed session string private. The script does
not write the session to disk.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os


def _read_api_id(value: int | None) -> int:
    if value:
        return value
    env_value = os.getenv("TELEGRAM_API_ID")
    if env_value:
        return int(env_value)
    return int(input("Telegram api_id: ").strip())


def _read_api_hash(value: str | None) -> str:
    if value:
        return value
    env_value = os.getenv("TELEGRAM_API_HASH")
    if env_value:
        return env_value
    return getpass.getpass("Telegram api_hash: ").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Telegram session string for a user account."
    )
    parser.add_argument("--api-id", type=int, help="Telegram app api_id")
    parser.add_argument("--api-hash", help="Telegram app api_hash")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    api_id = _read_api_id(args.api_id)
    api_hash = _read_api_hash(args.api_hash)

    try:
        from pyrogram import Client
    except ImportError as exc:
        raise SystemExit(
            "Pyrogram is not installed. Run this inside the project venv or Docker API container."
        ) from exc

    print("")
    print("Pyrogram will now ask for the phone number and Telegram login code.")
    print("Use a dedicated test Telegram account if this session is for autonomous tests.")
    print("")

    client = Client(
        name="session_string_generator",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    )
    await client.start()
    try:
        me = await client.get_me()
        session_string = await client.export_session_string()
    finally:
        await client.stop()

    username = f"@{me.username}" if getattr(me, "username", None) else "(no username)"
    print("")
    print(f"Logged in as: {getattr(me, 'first_name', '')} {username}")
    print("")
    print("SESSION_STRING_START")
    print(session_string)
    print("SESSION_STRING_END")
    print("")
    print("Keep this value secret. It gives access to this Telegram account.")


if __name__ == "__main__":
    asyncio.run(main())
