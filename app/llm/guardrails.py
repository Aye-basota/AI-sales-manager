import difflib


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


def apply_guardrails(text: str, last_messages: list[str]) -> str | None:
    if not check_length(text):
        return None
    if not check_no_forbidden_topics(text):
        return None
    if not check_anti_repetition(text, last_messages):
        return None
    return text
