"""Quality gates for first outbound messages."""

from __future__ import annotations

from typing import Any


BAD_INITIAL_MESSAGE_MARKERS = (
    "как у вас в",
    "it-компаниям, как у вас",
    "в вашем стеке",
    "безопасно и прозрачно выводить",
    "легально и прозрачно выводить",
    "выводить криптовалют",
    "криптовалюту в фиат",
    "обнал",
)


def needs_initial_message_retry(text: str) -> bool:
    """Return True when a first message sounds robotic or risky."""
    lower = (text or "").lower()
    return any(marker in lower for marker in BAD_INITIAL_MESSAGE_MARKERS)


def build_initial_message_retry_prompt(previous_text: str) -> str:
    """Build a corrective prompt after a weak first-message draft."""
    return (
        "Предыдущий вариант звучит слишком шаблонно или рискованно. "
        "Перепиши первое сообщение полностью.\n\n"
        "Жесткие правила:\n"
        "- не используй фразы про вывод криптовалюты в фиат;\n"
        "- не используй 'как у вас в ...' и 'в вашем стеке';\n"
        "- не делай вид, что точно знаешь процессы клиента;\n"
        "- начни спокойно, как живой человек;\n"
        "- задай один простой вопрос.\n\n"
        f"Предыдущий вариант:\n{previous_text}"
    )


def build_safe_initial_fallback(contact: Any | None = None) -> str:
    """Return a conservative first message if generation stays weak."""
    name = getattr(contact, "first_name", None) if contact else None
    greeting = f"Привет, {name}." if name else "Привет."
    return (
        f"{greeting}\n\n"
        "Пишу коротко: помогаем командам аккуратно выстроить первые диалоги "
        "с потенциальными клиентами без лишней ручной рутины.\n\n"
        "Как сейчас обычно начинается разговор с новым лидом?"
    )
