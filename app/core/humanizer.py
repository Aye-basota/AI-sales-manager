"""Human-like typing and message formatting utilities."""

import random
import re


def calculate_typing_delay(text: str, chars_per_min: tuple[float, float] = (200, 350)) -> int:
    """Return simulated typing delay for *text* in milliseconds.

    The delay is calculated using a random speed within *chars_per_min*.
    """
    if not text:
        return 0
    speed = random.uniform(*chars_per_min)
    chars_per_sec = speed / 60.0
    delay_sec = len(text) / chars_per_sec
    return int(delay_sec * 1000)


def calculate_thinking_delay(min_sec: int = 3, max_sec: int = 15) -> int:
    """Return a random thinking delay in milliseconds."""
    delay_sec = random.randint(min_sec, max_sec)
    return delay_sec * 1000


_SELF_CORRECTIONS = [
    "Точнее, ",
    "*точнее, ",
    "Уточню, ",
    "*уточню, ",
    "Поправка, ",
    "*поправка, ",
]


def maybe_self_correct(text: str, rate: float = 0.06) -> str:
    """With probability *rate*, prepend a casual self-correction prefix."""
    if not text or random.random() > rate:
        return text
    prefix = random.choice(_SELF_CORRECTIONS)
    return prefix + text


_CASUAL_MARKERS = [
    "кстати",
    "слушайте",
    "если честно",
]


def add_casual_markers(text: str, rate: float = 0.15) -> str:
    """Occasionally inject casual markers into *text*.

    A marker is inserted at the beginning of a random sentence with
    probability *rate*.  Only one marker is injected per call.
    """
    if not text or random.random() > rate:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if not sentences:
        return text

    idx = random.randrange(len(sentences))
    marker = random.choice(_CASUAL_MARKERS)
    sentence = sentences[idx].lstrip()
    # Preserve original leading whitespace if any
    leading_ws = sentences[idx][: len(sentences[idx]) - len(sentences[idx].lstrip())]

    # Capitalise marker when it starts the text or follows another sentence
    capitalised_marker = marker.capitalize() if idx == 0 else marker
    sentences[idx] = f"{leading_ws}{capitalised_marker}, {sentence[0].lower() if sentence else ''}{sentence[1:] if len(sentence) > 1 else ''}"

    return " ".join(sentences)
