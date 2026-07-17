"""Human-like typing and message formatting utilities."""

import random
import re


# Maximum time a human would plausibly keep the "typing..." indicator visible.
MAX_TYPING_DELAY_MS = 10_000


def calculate_typing_delay(
    text: str,
    chars_per_min: tuple[float, float] = (200, 350),
    max_ms: int = MAX_TYPING_DELAY_MS,
) -> int:
    """Return simulated typing delay for *text* in milliseconds.

    The delay is calculated using a random speed within *chars_per_min* and
    capped at *max_ms* so long messages do not keep the typing indicator
    visible for an unnaturally long time.
    """
    if not text:
        return 0
    speed = random.uniform(*chars_per_min)  # nosec B311
    chars_per_sec = speed / 60.0
    delay_sec = len(text) / chars_per_sec
    return min(int(delay_sec * 1000), max_ms)


def calculate_thinking_delay(min_sec: int = 3, max_sec: int = 12) -> int:
    """Return a random thinking delay in milliseconds.

    The thinking delay simulates the time before the person starts typing.
    It is applied *before* showing the typing indicator so the lead does not
    see "typing..." while the agent is "thinking".
    """
    delay_sec = random.randint(min_sec, max_sec)  # nosec B311
    return delay_sec * 1000


_SELF_CORRECTIONS = [
    "Точнее, ",
    "Уточню, ",
    "Поправка, ",
]


def maybe_self_correct(text: str, rate: float = 0.0) -> str:
    """With probability *rate*, prepend a casual self-correction prefix."""
    if not text or random.random() > rate:  # nosec B311
        return text
    prefix = random.choice(_SELF_CORRECTIONS)  # nosec B311
    return prefix + text


_CASUAL_MARKERS = [
    "кстати",
    "слушайте",
    "если честно",
]


def add_casual_markers(text: str, rate: float = 0.0) -> str:
    """Occasionally inject casual markers into *text*.

    A marker is inserted at the beginning of a random sentence with
    probability *rate*.  Only one marker is injected per call.
    """
    if not text or random.random() > rate:  # nosec B311
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if not sentences:
        return text

    idx = random.randrange(len(sentences))  # nosec B311
    marker = random.choice(_CASUAL_MARKERS)  # nosec B311
    sentence = sentences[idx].lstrip()
    # Preserve original leading whitespace if any
    leading_ws = sentences[idx][: len(sentences[idx]) - len(sentences[idx].lstrip())]

    # Capitalise marker when it starts the text or follows another sentence
    capitalised_marker = marker.capitalize() if idx == 0 else marker
    if sentence:
        first_char = sentence[0].lower()
        rest = sentence[1:] if len(sentence) > 1 else ""
        sentences[idx] = f"{leading_ws}{capitalised_marker}, {first_char}{rest}"
    else:
        sentences[idx] = f"{leading_ws}{capitalised_marker}, "

    return " ".join(sentences)


_DOUBLE_TAKE_TEMPLATES = [
    "Хотя подождите, вы же из {city}, там у вас, наверное, уже другие приоритеты?",
    "Кстати, {city} — оттуда у нас много запросов на эту тему.",
]


def maybe_double_take(text: str, city: str | None, rate: float = 0.0) -> str:
    """Append a double-take question or observation about city with probability rate."""
    if not city or random.random() > rate:  # nosec B311
        return text
    template = random.choice(_DOUBLE_TAKE_TEMPLATES)  # nosec B311
    return f"{text}\n\n{template.format(city=city)}"


def _split_paragraph_into_sentences(paragraph: str, max_chars: int) -> list[str]:
    """Split a long paragraph into sentence-sized chunks."""
    sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def _sentence_units(text: str) -> list[str]:
    """Return sentence-like units while keeping punctuation attached."""
    return [
        unit.strip()
        for unit in re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", text.strip())
        if unit.strip()
    ]


def maybe_split_message_into_burst(
    text: str,
    *,
    rate: float = 0.0,
    min_chars: int = 90,
    max_chunks: int = 2,
) -> list[str]:
    """Sometimes split one reply into a short human-like burst.

    The split is conservative: only sentence boundaries are used, both sides
    must carry useful text, and by default nothing changes. Callers opt in by
    passing a non-zero *rate*.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return [] if text == "" else [cleaned]
    if rate <= 0 or random.random() > rate:  # nosec B311
        return [cleaned]
    if max_chunks < 2 or len(cleaned) < min_chars:
        return [cleaned]
    if "\n\n" in cleaned:
        return [cleaned]

    sentences = _sentence_units(cleaned)
    if len(sentences) < 2:
        return [cleaned]

    candidates: list[tuple[str, str]] = []
    for idx in range(1, min(len(sentences), max_chunks + 1)):
        first = " ".join(sentences[:idx]).strip()
        second = " ".join(sentences[idx:]).strip()
        if len(first) >= 28 and len(second) >= 24:
            candidates.append((first, second))

    if not candidates:
        return [cleaned]

    first, second = random.choice(candidates)  # nosec B311
    return [first, second]


def split_message_into_chunks(
    text: str,
    max_chars: int = 350,
    max_chunks: int = 4,
    burst_rate: float = 0.0,
    burst_min_chars: int = 180,
) -> list[str]:
    """Split *text* into human-sized chunks.

    Splits on blank lines first, then breaks long paragraphs by sentences so
    that each chunk is small enough to feel like a natural message. If
    *burst_rate* is non-zero, a short one-paragraph reply may occasionally be
    split into two consecutive messages at a sentence boundary once it reaches
    *burst_min_chars*.
    """
    if not text:
        return []

    # Split on blank lines, preserving sentence groups
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if not paragraphs:
        return [text.strip()]

    # Break long paragraphs by sentences
    pieces: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_paragraph_into_sentences(paragraph, max_chars))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if not current:
            current = piece
            continue
        if len(current) + len(piece) + 2 <= max_chars:
            current = f"{current}\n\n{piece}"
        else:
            chunks.append(current)
            current = piece
    if current:
        chunks.append(current)

    if max_chunks > 0 and len(chunks) > max_chunks:
        head = chunks[: max_chunks - 1]
        tail = "\n\n".join(chunks[max_chunks - 1:])
        if len(tail) <= max_chars * 3:
            return [*head, tail]

    if len(chunks) == 1 and burst_rate > 0:
        return maybe_split_message_into_burst(
            chunks[0],
            rate=burst_rate,
            min_chars=burst_min_chars,
        )

    return chunks


def chunk_pause_seconds(min_sec: float = 2.0, max_sec: float = 6.0) -> float:
    """Return a random pause length between consecutive message chunks."""
    return random.uniform(min_sec, max_sec)  # nosec B311


def contains_markdown(text: str) -> bool:
    """Return True if *text* contains markdown characters."""
    return any(ch in text for ch in ("#", "*", "_", "`"))


def remove_markdown(text: str) -> str:
    """Remove common markdown formatting from *text*."""
    # Remove bold/italic markers around text
    text = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}(.*?)_{1,2}", r"\1", text)
    # Remove inline code/backticks
    text = re.sub(r"`+([^`]*?)`+", r"\1", text)
    # Remove headers
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    # Remove stray leading asterisks (e.g. from self-corrections)
    text = re.sub(r"^\*+", "", text)
    text = re.sub(r"\s\*+", " ", text)
    return text


def format_message(text: str, city: str | None = None) -> str:
    """Apply casual markers, self-correction, double-take and ensure plain text.

    The message is humanized and stripped of any markdown formatting.
    """
    if not text:
        return text

    if contains_markdown(text):
        text = remove_markdown(text)

    text = maybe_self_correct(text)
    text = add_casual_markers(text)
    text = maybe_double_take(text, city)
    return text
