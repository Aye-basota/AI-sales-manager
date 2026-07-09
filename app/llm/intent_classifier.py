import logging
import re

from app.llm.engine import LLMEngine
from app.llm.prompts import build_intent_classification_prompt

logger = logging.getLogger(__name__)

VALID_INTENTS = {
    "meeting_intent",
    "question",
    "objection",
    "positive",
    "negative",
    "informational",
}


HARD_NEGATIVE_PATTERNS = (
    r"\bне\s+пишите\b",
    r"\bбольше\s+не\s+пишите\b",
    r"\bне\s+надо\b",
    r"\bне\s+нужно\b",
    r"\bне\s+интересно\b",
    r"\bне\s+актуально\b",
    r"\bне\s+беспоко(?:й|и)те\b",
    r"\bотстаньте\b",
    r"\bудалите\s+(?:меня|мой\s+контакт|мои\s+данные)\b",
    r"\bstop\b",
    r"\bunsubscribe\b",
)

MEETING_PATTERNS = (
    r"\bдава(?:й|йте)\s+созвон",
    r"\bсозвон(?:им|иться|иться)?\b",
    r"\bсозвонимся\b",
    r"\bвстретимся\b",
    r"\bвстреч[ауи]\b",
    r"\bдемо\b",
    r"\bзвонок\b",
    r"\bколл\b",
)


def _classify_intent_rule_based(message: str) -> str | None:
    lower = message.lower()
    if lower.strip(" .,!?:;") in {"нет", "no", "stop"}:
        return "negative"
    if any(re.search(pattern, lower) for pattern in HARD_NEGATIVE_PATTERNS):
        return "negative"
    if any(re.search(pattern, lower) for pattern in MEETING_PATTERNS):
        return "meeting_intent"
    return None


async def classify_intent(message: str, engine: LLMEngine) -> str:
    rule_based = _classify_intent_rule_based(message)
    if rule_based:
        return rule_based

    prompt = build_intent_classification_prompt(message)
    messages = [
        {
            "role": "system",
            "content": "Ты классифицируешь намерения. Верни только метку.",
        },
        {"role": "user", "content": prompt},
    ]

    result = await engine.generate_with_fallback(messages)
    raw_text = result.get("text", "").strip().lower()

    # Try to extract a label by looking for any valid intent in the text.
    # Prefer exact matches, then substring matches.
    cleaned = re.sub(r"[^a-z_\s]", "", raw_text)
    words = cleaned.split()

    for word in words:
        if word in VALID_INTENTS:
            return word

    for intent in VALID_INTENTS:
        if intent in raw_text:
            return intent

    # Default fallback if nothing matched
    logger.warning(
        "Could not classify intent for message, defaulting to 'informational': %s",
        message,
    )
    return "informational"
