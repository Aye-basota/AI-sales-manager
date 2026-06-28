import difflib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GuardrailsResult:
    approved: bool
    text: str | None
    violations: list[str]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.approved and self.text == other
        if other is None:
            return not self.approved
        if isinstance(other, GuardrailsResult):
            return (
                self.approved == other.approved
                and self.text == other.text
                and self.violations == other.violations
            )
        return NotImplemented


def check_length(text: str, max_words: int = 300) -> bool:
    words = text.split()
    return len(words) <= max_words


def check_no_forbidden_topics(
    text: str,
    forbidden: list[str] | None = None,
) -> bool:
    if forbidden is None:
        forbidden = [
            "политика",
            "религия",
            "расизм",
            "насилие",
            "порнография",
            "наркотики",
        ]
    lower_text = text.lower()
    for topic in forbidden:
        if topic in lower_text:
            return False
    return True


def check_anti_repetition(
    text: str,
    last_messages: list[str],
    threshold: float = 0.8,
) -> bool:
    if not last_messages:
        return True
    for prev in last_messages:
        similarity = difflib.SequenceMatcher(None, text, prev).ratio()
        if similarity >= threshold:
            return False
    return True


def check_no_bot_words(text: str, forbidden: list[str] | None = None) -> bool:
    if forbidden is None:
        forbidden = ["бот", "ассистент", "искусственный интеллект", "нейросеть", "я ии"]
    lower_text = text.lower()
    for word in forbidden:
        # Match whole words only to avoid false positives like "работаю" or "робот".
        pattern = r"(^|\s|[()])" + re.escape(word) + r"($|[\s,.!?;:)])"
        if re.search(pattern, lower_text):
            return False
    return True


def check_no_markdown(text: str) -> bool:
    return not any(ch in text for ch in ("#", "*", "_", "`"))


def check_no_emoji(text: str) -> bool:
    """Return True if *text* contains no emoji characters."""
    for ch in text:
        cat = ch.category if hasattr(ch, "category") else None
        if cat in ("So",):
            return False
        code = ord(ch)
        # Common emoji ranges
        if (
            0x1F600 <= code <= 0x1F64F
            or 0x1F300 <= code <= 0x1F5FF
            or 0x1F680 <= code <= 0x1F6FF
            or 0x1F1E0 <= code <= 0x1F1FF
            or 0x2600 <= code <= 0x26FF
            or 0x2700 <= code <= 0x27BF
            or 0xFE00 <= code <= 0xFE0F
            or 0x1F900 <= code <= 0x1F9FF
            or 0x1FA00 <= code <= 0x1FA6F
            or 0x1FA70 <= code <= 0x1FAFF
        ):
            return False
    return True


def check_no_cjk_arabic(text: str) -> bool:
    """Return True if *text* contains no CJK or Arabic script characters."""
    for ch in text:
        code = ord(ch)
        # CJK Unified Ideographs
        if 0x4E00 <= code <= 0x9FFF:
            return False
        # Hiragana / Katakana
        if 0x3040 <= code <= 0x309F or 0x30A0 <= code <= 0x30FF:
            return False
        # Hangul
        if 0xAC00 <= code <= 0xD7AF:
            return False
        # Arabic / Arabic Supplement / Extended-A
        if (
            0x0600 <= code <= 0x06FF
            or 0x0750 <= code <= 0x077F
            or 0x08A0 <= code <= 0x08FF
        ):
            return False
    return True


def evaluate_guardrails(text: str, last_messages: list[str]) -> GuardrailsResult:
    violations: list[str] = []

    if not check_length(text):
        violations.append("length")
    if not check_no_forbidden_topics(text):
        violations.append("forbidden_topic")
    if not check_anti_repetition(text, last_messages):
        violations.append("repetition")
    if not check_no_bot_words(text):
        violations.append("bot_words")
    if not check_no_markdown(text):
        violations.append("markdown")
    if not check_no_emoji(text):
        violations.append("emoji")
    if not check_no_cjk_arabic(text):
        violations.append("foreign_script")

    if violations:
        return GuardrailsResult(approved=False, text=None, violations=violations)
    return GuardrailsResult(approved=True, text=text, violations=[])


def apply_guardrails(text: str, last_messages: list[str]) -> str | None:
    result = evaluate_guardrails(text, last_messages)
    if result.approved:
        return result.text
    return None
