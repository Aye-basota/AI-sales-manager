import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass

from app.llm.context import looks_like_prompt_leak

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
        forbidden = [
            "бот",
            "ассистент",
            "искусственный интеллект",
            "нейросеть",
            "я ии",
            "ai",
        ]
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
        cat = unicodedata.category(ch)
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


def check_max_questions(text: str, max_questions: int = 1) -> bool:
    """Return True when the message does not interrogate the lead too much."""
    return text.count("?") <= max_questions


def check_no_banned_sales_phrases(text: str) -> bool:
    """Block phrases that make Telegram outreach sound templated."""
    banned = (
        "как сейчас решаете эту задачу",
        "в вашем стеке",
        "it-компаниям, как у вас",
        "как у вас в",
        "понял, что у вас",
        "понимаю, что у вас",
    )
    lower_text = text.lower()
    return not any(phrase in lower_text for phrase in banned)


def check_no_unverified_personalization(text: str) -> bool:
    """Block fake familiarity or unsupported assumptions about a lead."""
    lower_text = text.lower()
    patterns = (
        r"\bработа(?:ешь|ете)\s+в\s+(?:it|айти)\b",
        r"\bнаверное,\s+(?:знаешь|знаете|понимаешь|понимаете)\b",
        r"\bзнаком(?:ы|а|)\s+с\s+[^.?!]+[,—-]\s*уважа",
        r"\bзнаком\s+с\s+(?:вашей|вашим|вашими|твоей|твоим)\b",
        r"\bзнаю\s+(?:вашу|твою)\s+компан",
        r"\bуважаю\s+(?:ваш|твой|вашу|твою)\b",
        r"\bвидел(?:а)?\s+(?:ваш|твой)\s+профиль\b",
        r"\bсмотрел(?:а)?\s+(?:ваш|твой)\s+(?:сайт|профиль|канал)\b",
    )
    return not any(re.search(pattern, lower_text) for pattern in patterns)


def check_no_prompt_leakage(text: str) -> bool:
    """Block responses that expose internal prompts, roles, or rules."""
    if looks_like_prompt_leak(text):
        return False

    lower_text = text.lower()
    patterns = (
        r"\b(?:system|developer|assistant|user)\s*:",
        r'"role"\s*:\s*"(?:system|developer|assistant|user)"',
        r"\b(?:system|developer)\s+(?:message|prompt|instructions?)\b",
        r"(?:мои|служебные|системные)\s+инструкц",
        r"(?:не могу|не буду)\s+(?:раскрыть|показать|вывести)\s+.*(?:промпт|инструкц)",
        r"(?:раскрыть|показать|вывести)\s+.*(?:промпт|инструкц)",
        r"правил[ао]\s+генерац",
        r"критерий\s+успеха\s*:",
        r"цель\s+диалога\s*:",
        r"цель\s+переписки\s*:",
        r"разрешенн\w*\s+следующ\w*\s+шаг\s*:",
        r"тональность\s*:",
        r"коротко\s+по\s+сути\s*:\s*(?:пригласить|назначить|получить|довести|предложить)\b",
        r"пригласить\s+и\s+назнач(?:ить|ит)\s+демонстрац",
    )
    return not any(re.search(pattern, lower_text) for pattern in patterns)


def check_no_unsupported_product_claims(text: str) -> bool:
    """Block factual product claims that must not be invented by the model."""
    lower_text = text.lower()
    patterns = (
        r"интеграц\w*\s+с\s+[^.?!]+(?:работа|поддерж|есть|можно)",
        r"готов\w*\s+коннектор",
        r"через\s+вебхук",
        r"есть\s+реальн\w*\s+кейс",
        r"сократил\w*[^.?!]*\d",
        r"\+\d+\s*%",
        r"в\s+\d+\s+раз",
        r"зашифрован\w*\s+вид",
        r"доступ\s+только\s+у\s+вас",
        r"без\s+сохранения\s+сообщен",
        r"официальн\w*\s+telegram\s+bot\s+api",
        r"\blinkedin\b",
        r"\bemail\b",
        r"не\s+пропускает\s+ни\s+одного",
        r"всегда\s+начинает",
        r"недавно\s+делал\w*",
        r"для\s+похож\w+\s+(?:места|компании|проекта|формата)",
        r"у\s+нас\s+есть\s+готов\w+\s+(?:дизайн|макет|концепц)",
        r"с\s+соблюдением\s+сроков",
        r"без\s+лишних\s+согласован",
    )
    return not any(re.search(pattern, lower_text) for pattern in patterns)


def check_no_unsupported_creative_work(text: str) -> bool:
    """Block invented creative/design deliverables in plain outreach replies."""
    lower_text = text.lower()
    patterns = (
        r"вот\s+(?:два|три|несколько)\s+вариант\w*",
        r"первый\s+вариант[^.?!]+(?:второй|ещ[её])",
        r"можем\s+сделать\s+дизайн\s+",
        r"предлож(?:у|им)\s+(?:дизайн|концепц|макет)",
        r"использовал\w*[^.?!]*(?:цвет|шрифт|паттерн|график|иллюстрац)",
        r"стаканчик\s+должен\s+быть",
        r"сразу\s+понятно[^.?!]*(?:дизайн|стаканчик|макет|концепц)",
    )
    return not any(re.search(pattern, lower_text) for pattern in patterns)


def check_no_out_of_scope_seller_claims(text: str) -> bool:
    """Block invented assortment/product consulting outside the manager's role."""
    lower_text = text.lower()
    patterns = (
        r"\b(?:подбер[её]м|подберу|предлож(?:у|им)|посовет(?:ую|уем))\b[^.?!]*"
        r"(?:ассортимент|товар|вариант|модель|материал|объ[её]м|цвет|крышк)",
        r"\b(?:можем|готовы)\b[^.?!]*(?:подобрать|предложить|посоветовать)\b[^.?!]*"
        r"(?:товар|вариант|модель|материал|объ[её]м|цвет)",
        r"\b(?:лучше\s+взять|вам\s+подойд[её]т|я\s+бы\s+советовал)\b[^.?!]*(?:мл|литр|материал|цвет|модель|вариант)",
        r"\b(?:покажу|пришлю|отправлю)\b[^.?!]*(?:ассортимент|каталог|линейк\w*|варианты\s+товар)",
    )
    return not any(re.search(pattern, lower_text) for pattern in patterns)


def check_no_unverified_pricing(text: str) -> bool:
    """Block exact prices unless pricing is handled by a dedicated verified source."""
    lower_text = text.lower()
    patterns = (
        r"\d[\d\s.,]*(?:₽|руб\.?|р\.|доллар\w*|usd|\$|€|eur|евро)",
        r"(?:стоит|цена|ценник|прайс|бюджет|стоимость)\D{0,24}\d[\d\s.,]*",
        r"\d[\d\s.,]*\s*(?:за|/)\s*(?:штук\w*|стакан\w*|контакт\w*|лид\w*|месяц\w*)",
    )
    return not any(re.search(pattern, lower_text) for pattern in patterns)


def check_no_unsupported_actions(text: str) -> bool:
    """Block promises to send files/media that the Telegram sender cannot actually attach."""
    lower_text = text.lower()
    patterns = (
        r"\b(?:присылаю|отправляю|прикрепляю)\b[^.?!]*(?:фото|файл|каталог|презентац|пример)",
        r"\b(?:send|sending|attach|attaching)\b[^.?!]*(?:photo|file|catalog|deck|presentation|example)",
        r"вот\s+(?:фото|примеры|каталог)",
    )
    return not any(re.search(pattern, lower_text) for pattern in patterns)


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
    if not check_max_questions(text):
        violations.append("too_many_questions")
    if not check_no_banned_sales_phrases(text):
        violations.append("banned_sales_phrase")
    if not check_no_unverified_personalization(text):
        violations.append("unverified_personalization")
    if not check_no_prompt_leakage(text):
        violations.append("prompt_leakage")
    if not check_no_unsupported_product_claims(text):
        violations.append("unsupported_product_claim")
    if not check_no_unsupported_creative_work(text):
        violations.append("unsupported_creative_work")
    if not check_no_out_of_scope_seller_claims(text):
        violations.append("out_of_scope_seller_claim")
    if not check_no_unverified_pricing(text):
        violations.append("unverified_pricing")
    if not check_no_unsupported_actions(text):
        violations.append("unsupported_action")
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
