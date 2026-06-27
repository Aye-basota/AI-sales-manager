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


async def classify_intent(message: str, engine: LLMEngine) -> str:
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
