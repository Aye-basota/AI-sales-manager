"""Quality gates for no-reply follow-up messages."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from app.llm.context import extract_offer_summary


FOLLOW_UP_GREETING_PREFIXES = (
    "привет",
    "здравствуйте",
    "добрый день",
    "доброе утро",
    "добрый вечер",
    "hello",
    "hi",
)

LOW_VALUE_FOLLOW_UP_MARKERS = (
    "если вдруг интересно",
    "если хочешь, могу рассказать подробнее",
    "если хотите, могу рассказать подробнее",
    "могу рассказать подробнее",
)


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def _too_similar_to_previous(text: str, previous_text: str) -> bool:
    current = _normalize(text)
    previous = _normalize(previous_text)
    if len(current) < 40 or len(previous) < 40:
        return False
    return SequenceMatcher(None, current, previous).ratio() >= 0.72


def needs_follow_up_retry(text: str, last_agent_message: str = "") -> bool:
    """Return True when a follow-up is likely to feel like a second first touch."""
    lower = _normalize(text)
    if not lower:
        return True
    if any(lower.startswith(prefix) for prefix in FOLLOW_UP_GREETING_PREFIXES):
        return True
    if any(marker in lower for marker in LOW_VALUE_FOLLOW_UP_MARKERS):
        return True
    return _too_similar_to_previous(text, last_agent_message)


def build_follow_up_retry_prompt(previous_text: str, last_agent_message: str) -> str:
    """Build a corrective prompt after a weak follow-up draft."""
    return (
        "Предыдущий follow-up звучит как повтор первого сообщения или слишком пусто. "
        "Перепиши его полностью.\n\n"
        "Жесткие правила:\n"
        "- не начинай с приветствия;\n"
        "- не повторяй предыдущую реплику и не пересказывай ее теми же словами;\n"
        "- не пиши, что клиент заинтересовался, забыл или обещал ответить;\n"
        "- не используй фразы 'если вдруг интересно' и 'могу рассказать подробнее';\n"
        "- сделай одно короткое повторное касание после молчания;\n"
        "- дай человеку легкий выход, если тема неактуальна.\n\n"
        f"Предыдущая реплика менеджера:\n{last_agent_message}\n\n"
        f"Слабый follow-up:\n{previous_text}"
    )


def build_safe_follow_up_fallback(
    contact: Any | None = None,
    script: Any | None = None,
) -> str:
    """Return a conservative no-reply follow-up if generation stays weak."""
    name = getattr(contact, "first_name", None) if contact else None
    prefix = f"{name}, " if name else ""
    offer = extract_offer_summary(script, max_chars=160)
    return (
        f"{prefix}оставлю коротко на случай, если тема все же актуальна: {offer}. "
        "Если сейчас не нужно, больше не буду отвлекать."
    )
