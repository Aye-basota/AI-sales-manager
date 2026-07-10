"""Генератор session string для Telegram seller-аккаунта.

Запускается внутри Docker-контейнера. Подменяет pyrogram.utils.ainput так,
чтобы код подтверждения и пароль 2FA брался из файлов вместо stdin.
Это позволяет работать в неинтерактивном терминале.
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

from pyrogram import Client
import pyrogram.utils
import pyrogram.client


INPUT_DIR = Path(
    os.getenv(
        "TELEGRAM_SESSION_INPUT_DIR",
        str(Path(tempfile.gettempdir()) / "ai-sales-manager-session"),
    )
)
CODE_FILE = INPUT_DIR / "telegram_code.txt"
TWOFA_FILE = INPUT_DIR / "telegram_2fa.txt"
POLL_INTERVAL = 2
TIMEOUT = 300


async def wait_for_file(path: Path, label: str) -> str:
    INPUT_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    print(f"\n[ОЖИДАНИЕ] Введите {label} и запишите его в файл {path}")
    print("          Пример команды в другом терминале:")
    print(f"          docker-compose exec api bash -c 'echo 12345 > {path}'")
    print(f"[ОЖИДАНИЕ] Ожидаю до {TIMEOUT} секунд...\n", flush=True)

    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                value = f.read().strip()
            if value:
                try:
                    path.unlink()
                except OSError:
                    pass
                print(f"[ПОЛУЧЕНО] {label}: {value}\n", flush=True)
                return value
        await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Не дождались {label} в файле {path}")


async def patched_ainput(prompt: str = "", *, hide: bool = False):
    if "password" in prompt.lower() or hide:
        return await wait_for_file(TWOFA_FILE, "пароль 2FA")
    return await wait_for_file(CODE_FILE, "код подтверждения Telegram")


async def main():
    api_id_raw = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("SELLER_PHONE")

    if not api_id_raw or not api_hash:
        print("Ошибка: не заданы TELEGRAM_API_ID / TELEGRAM_API_HASH", file=sys.stderr)
        sys.exit(1)
    if not phone:
        print("Ошибка: не задана переменная SELLER_PHONE", file=sys.stderr)
        sys.exit(1)

    api_id = int(api_id_raw)

    # Подменяем ввод, чтобы работать без интерактивного stdin
    pyrogram.utils.ainput = patched_ainput
    pyrogram.client.ainput = patched_ainput

    print(f"Запускаю авторизацию для номера {phone}...", flush=True)

    client = Client(
        name="session_gen",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone,
        in_memory=True,
    )

    async with client as app:
        session = await app.export_session_string()
        print("\n=== ВАША SESSION STRING ===")
        print(session)
        print("===========================\n")


if __name__ == "__main__":
    asyncio.run(main())
