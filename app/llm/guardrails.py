import difflib
import logging
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
        if word in lower_text:
            return False
    return True


def check_no_markdown(text: str) -> bool:
    return not any(ch in text for ch in ("#", "*", "_", "`"))


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

    if violations:
        return GuardrailsResult(approved=False, text=None, violations=violations)
    return GuardrailsResult(approved=True, text=text, violations=[])


def apply_guardrails(text: str, last_messages: list[str]) -> str | None:
    result = evaluate_guardrails(text, last_messages)
    if result.approved:
        return result.text
    return None
