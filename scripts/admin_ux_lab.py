"""Safe admin bot UX smoke lab.

This script does not connect to Telegram. It calls admin bot handlers with small
fake Telegram objects and writes a markdown report. It is meant to catch the
human-facing failures that unit tests can miss: unclear first screen, missing
fallbacks, stale buttons and broken menu routing.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable


OUTPUT = Path(__file__).resolve().parent / ".admin-ux-lab" / "latest.md"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.bots import admin_bot  # noqa: E402


@dataclass
class ScenarioResult:
    name: str
    status: str
    details: str = ""


class FakeMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.answers: list[tuple[str, dict[str, Any]]] = []
        self.from_user = SimpleNamespace(is_bot=False)

    async def answer(self, text: str, **kwargs: Any) -> SimpleNamespace:
        self.answers.append((text, kwargs))
        return SimpleNamespace(text=text, kwargs=kwargs)


class FakeCallback:
    def __init__(self, data: str, message: FakeMessage | None = None) -> None:
        self.data = data
        self.message = message or FakeMessage()
        self.answers: list[tuple[str | None, dict[str, Any]]] = []

    async def answer(self, text: str | None = None, **kwargs: Any) -> None:
        self.answers.append((text, kwargs))


class FakeState:
    def __init__(self, current_state: str | None = None) -> None:
        self.current_state = current_state
        self.cleared = False

    async def get_state(self) -> str | None:
        return self.current_state

    async def clear(self) -> None:
        self.current_state = None
        self.cleared = True

    async def set_state(self, state: Any) -> None:
        self.current_state = str(state)

    async def update_data(self, **kwargs: Any) -> None:
        return None


def _assert_contains(text: str, *needles: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"Missing expected text: {missing}. Got: {text[:500]}")


async def _run(name: str, scenario: Callable[[], Awaitable[str]]) -> ScenarioResult:
    try:
        details = await scenario()
        return ScenarioResult(name=name, status="PASS", details=details)
    except Exception as exc:
        return ScenarioResult(name=name, status="FAIL", details=str(exc))


async def _start_screen() -> str:
    message = FakeMessage("/start")
    await admin_bot.cmd_start(message)
    text, kwargs = message.answers[-1]
    _assert_contains(text, "Сценарий", "Контакты", "Кампания", "/help")
    if kwargs.get("reply_markup") is None:
        raise AssertionError("Start screen did not attach the main menu")
    return text


async def _help_screen() -> str:
    message = FakeMessage("/help")
    await admin_bot.cmd_help(message)
    text, kwargs = message.answers[-1]
    _assert_contains(text, "/cancel", "/conversations <contact_id>", "Горячие лиды")
    if kwargs.get("reply_markup") is None:
        raise AssertionError("Help screen did not attach the main menu")
    return text


async def _unknown_message() -> str:
    message = FakeMessage("что это вообще такое")
    await admin_bot.handle_unknown_message(message, FakeState())
    text, kwargs = message.answers[-1]
    _assert_contains(text, "Не понял команду", "сценарий", "кампанию")
    if kwargs.get("reply_markup") is None:
        raise AssertionError("Unknown message fallback did not attach the main menu")
    return text


async def _unknown_inside_wizard() -> str:
    message = FakeMessage("не туда")
    await admin_bot.handle_unknown_message(message, FakeState("ScriptCreateFSM:tone"))
    text, _ = message.answers[-1]
    _assert_contains(text, "открыт мастер", "/cancel")
    return text


async def _cancel_active_wizard() -> str:
    state = FakeState("CampaignCreateFSM:name")
    message = FakeMessage("/cancel")
    await admin_bot.cmd_cancel(message, state)
    text, kwargs = message.answers[-1]
    _assert_contains(text, "остановил текущий мастер")
    if not state.cleared:
        raise AssertionError("/cancel did not clear FSM state")
    if kwargs.get("reply_markup") is None:
        raise AssertionError("/cancel did not return the main menu")
    return text


async def _command_switches_active_wizard() -> str:
    state = FakeState("CSVImportFSM:waiting_file")
    message = FakeMessage("/help")
    handled = await admin_bot._dispatch_navigation_override(message, state)
    if not handled:
        raise AssertionError("Command inside wizard was not intercepted")
    if not state.cleared:
        raise AssertionError("Command switch did not clear the previous wizard")
    text, kwargs = message.answers[-1]
    _assert_contains(text, "Короткая схема", "/cancel")
    if kwargs.get("reply_markup") is None:
        raise AssertionError("Command switch did not return the main menu")
    return text


async def _menu_switches_active_wizard() -> str:
    state = FakeState("ScriptCreateFSM:name")
    message = FakeMessage(admin_bot.MENU_UPLOAD)
    handled = await admin_bot._dispatch_navigation_override(message, state)
    if not handled:
        raise AssertionError("Menu button inside wizard was not intercepted")
    if not state.current_state:
        raise AssertionError("Upload menu did not enter its own wizard")
    text, _ = message.answers[-1]
    _assert_contains(text, "Отправьте CSV", "telegram_user_id")
    return text


async def _unknown_command_inside_wizard() -> str:
    state = FakeState("ScriptCreateFSM:name")
    message = FakeMessage("/wat")
    handled = await admin_bot._dispatch_navigation_override(message, state)
    if not handled:
        raise AssertionError("Unknown command inside wizard was not intercepted")
    if state.cleared:
        raise AssertionError("Unknown command should not clear the current wizard")
    text, _ = message.answers[-1]
    _assert_contains(text, "не будет записана как ответ", "/cancel")
    return text


async def _unknown_callback() -> str:
    callback = FakeCallback("stale:button")
    await admin_bot.handle_unknown_callback(callback)
    if not callback.answers:
        raise AssertionError("Unknown callback did not answer callback query")
    text, kwargs = callback.answers[-1]
    _assert_contains(text or "", "Не понял кнопку")
    if not kwargs.get("show_alert"):
        raise AssertionError("Unknown callback should use show_alert=True")
    message_text, message_kwargs = callback.message.answers[-1]
    _assert_contains(message_text, "кнопка устарела")
    if message_kwargs.get("reply_markup") is None:
        raise AssertionError("Unknown callback fallback did not attach the main menu")
    return message_text


async def _menu_routing_compatibility() -> str:
    calls: list[tuple[str, bool]] = []

    async def stateful_handler(message: FakeMessage, state: FakeState) -> None:
        calls.append((message.text or "", state is not None))

    async def plain_handler(message: FakeMessage) -> None:
        calls.append((message.text or "", False))

    original_upload = admin_bot.MENU_HANDLERS[admin_bot.MENU_UPLOAD]
    original_scripts = admin_bot.MENU_HANDLERS["Scripts"]
    admin_bot.MENU_HANDLERS[admin_bot.MENU_UPLOAD] = stateful_handler
    admin_bot.MENU_HANDLERS["Scripts"] = plain_handler
    try:
        await admin_bot.handle_menu_button(FakeMessage(admin_bot.MENU_UPLOAD), FakeState())
        await admin_bot.handle_menu_button(FakeMessage("Scripts"), FakeState())
    finally:
        admin_bot.MENU_HANDLERS[admin_bot.MENU_UPLOAD] = original_upload
        admin_bot.MENU_HANDLERS["Scripts"] = original_scripts

    if calls != [(admin_bot.MENU_UPLOAD, True), ("Scripts", False)]:
        raise AssertionError(f"Unexpected menu routing calls: {calls}")
    return "Russian stateful menu and legacy English menu both route correctly"


def _write_report(results: list[ScenarioResult]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Admin UX Lab",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## {result.status}: {result.name}",
                "",
                "```text",
                result.details,
                "```",
                "",
            ]
        )
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


async def main() -> int:
    scenarios = [
        ("start screen explains product flow", _start_screen),
        ("help screen explains commands and exit", _help_screen),
        ("unknown message gets helpful fallback", _unknown_message),
        ("unknown wizard text points to cancel", _unknown_inside_wizard),
        ("cancel exits active wizard", _cancel_active_wizard),
        ("command switches active wizard", _command_switches_active_wizard),
        ("menu switches active wizard", _menu_switches_active_wizard),
        ("unknown command is not saved as answer", _unknown_command_inside_wizard),
        ("stale callback gets explicit fallback", _unknown_callback),
        ("menu routing keeps compatibility", _menu_routing_compatibility),
    ]
    results = [await _run(name, scenario) for name, scenario in scenarios]
    _write_report(results)

    print(f"Admin UX lab finished. Report: {OUTPUT}")
    for result in results:
        print(f"{result.status:4} {result.name}")
    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
