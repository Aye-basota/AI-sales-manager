"""Quality gates for first outbound messages."""

from __future__ import annotations

from typing import Any

from app.llm.context import extract_offer_summary


BAD_INITIAL_MESSAGE_MARKERS = (
    "как у вас в",
    "it-компаниям, как у вас",
    "в вашем стеке",
    "работаешь в it",
    "работаете в it",
    "работаешь в айти",
    "работаете в айти",
    "наверное, знаешь",
    "наверное, знаете",
    "знакомы с ",
    "знаком с вашей",
    "знаком с вашим",
    "знаю вашу компан",
    "уважаю ваш подход",
    "уважаю вашу",
    "видел ваш профиль",
    "видела ваш профиль",
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
        "- не делай вид, что знаком с компанией, профилем или подходом клиента;\n"
        "- не выдумывай отрасль, должность, опыт или личный контекст клиента;\n"
        "- начни спокойно, как живой человек;\n"
        "- задай один простой вопрос.\n\n"
        f"Предыдущий вариант:\n{previous_text}"
    )


def _offer_context(script: Any | None = None) -> str:
    return extract_offer_summary(script, max_chars=180).replace(
        "помогаем решить задачу",
        "помогаем с вашей задачей",
    )


def build_safe_initial_fallback(
    contact: Any | None = None,
    script: Any | None = None,
) -> str:
    """Return a conservative first message if generation stays weak."""
    name = getattr(contact, "first_name", None) if contact else None
    greeting = f"Привет, {name}." if name else "Привет."
    offer = _offer_context(script)
    return (
        f"{greeting} Пишу коротко: {offer}. "
        "Если актуально, могу в двух словах рассказать, как это обычно организуем."
    )
