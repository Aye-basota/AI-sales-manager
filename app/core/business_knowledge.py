"""Business-context audit and owner clarification helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.llm.context import collapse_whitespace, sanitize_context_text


UNKNOWN_ANSWER_MARKERS = (
    "не знаю",
    "неизвестно",
    "нет данных",
    "уточнить",
    "пока нет",
    "n/a",
    "unknown",
)

AUDIT_QUESTION_LIMIT = 6
AUDIT_QUESTION_MIN = 3


@dataclass(frozen=True)
class KnowledgeArea:
    key: str
    label_ru: str
    question_ru: str
    triggers: tuple[str, ...]
    context_markers: tuple[str, ...]
    claim_patterns: tuple[str, ...] = ()


KNOWLEDGE_AREAS: tuple[KnowledgeArea, ...] = (
    KnowledgeArea(
        key="pricing",
        label_ru="цены, скидки и минимальный заказ",
        question_ru=(
            "Какие цены, минимальный заказ и правила скидок можно уверенно называть?"
        ),
        triggers=(
            r"\bцен(?:а|у|ы|е|ой)?\b",
            r"ценник",
            r"прайс",
            r"расцен",
            r"стоим",
            r"сколько\s+стоит",
            r"скидк",
            r"бюджет",
            r"дорого",
            r"минимальн\w*\s+бюджет",
            r"минимальн\w*\s+заказ",
        ),
        context_markers=(
            "цена",
            "стоимость",
            "прайс",
            "расцен",
            "скидк",
            "бюджет",
            "минимальный бюджет",
            "минимальный заказ",
            "мин. заказ",
        ),
        claim_patterns=(
            r"\d[\d\s.,]*(?:₽|руб\.?|р\.|usd|\$|€|eur)",
            r"скидк\w*[^.?!]*\d",
        ),
    ),
    KnowledgeArea(
        key="delivery",
        label_ru="доставка, регионы и сроки",
        question_ru=(
            "Куда доставляете, какие обычные сроки и что нельзя обещать по срочности?"
        ),
        triggers=(
            r"доставк",
            r"привез",
            r"отгруз",
            r"к\s+(?:пятниц|понедельник|вторник|сред|четверг|суббот|воскрес)",
            r"срок",
            r"успеет",
            r"казахстан",
            r"регион",
        ),
        context_markers=("доставка", "доставляем", "срок", "отгруз", "регион"),
        claim_patterns=(
            r"(?:доставляем|осуществляем\s+доставку|привез[её]м)[^.?!]*",
            r"успеем[^.?!]*",
        ),
    ),
    KnowledgeArea(
        key="assortment",
        label_ru="ассортимент, материалы, размеры, крышки",
        question_ru=(
            "Какие типы товаров, материалы, размеры, крышки и ограничения ассортимента есть?"
        ),
        triggers=(
            r"какие\s+(?:стакан|вариант|тип)",
            r"ассортимент",
            r"бумажн",
            r"биоразлагаем",
            r"горяч",
            r"холодн",
            r"крышк",
            r"материал",
            r"размер",
            r"цвет",
            r"об[ъь]ем",
        ),
        context_markers=(
            "ассортимент",
            "бумаж",
            "биоразлага",
            "горяч",
            "холодн",
            "крышк",
            "материал",
            "размер",
            "цвет",
            "объем",
            "объём",
        ),
        claim_patterns=(
            r"есть\s+[^.?!]*(?:бумажн|биоразлагаем|крышк|горяч|холодн)",
            r"прода[её]м\s+оба\s+тип",
            r"широк\w+\s+ассортимент",
        ),
    ),
    KnowledgeArea(
        key="branding",
        label_ru="брендирование и кастомизация",
        question_ru=(
            "Доступно ли брендирование, какие условия, сроки и минимальные тиражи?"
        ),
        triggers=(r"брендирован", r"логотип", r"печать", r"кастом", r"дизайн"),
        context_markers=("брендирован", "логотип", "печать", "кастом", "дизайн"),
        claim_patterns=(
            r"брендирован\w+\s+возмож",
            r"(?:сделаем|нанес[её]м)[^.?!]*(?:логотип|печать)",
        ),
    ),
    KnowledgeArea(
        key="documents",
        label_ru="сертификаты и документы",
        question_ru=(
            "Какие сертификаты, закрывающие документы и требования для юрлиц есть?"
        ),
        triggers=(r"сертификат", r"документ", r"юрлиц", r"бухгалтер", r"закрывающ"),
        context_markers=("сертификат", "документ", "юрлиц", "бухгалтер", "закрывающ"),
        claim_patterns=(
            r"есть\s+[^.?!]*(?:сертификат|документ)",
            r"предоставляем\s+[^.?!]*(?:сертификат|документ)",
        ),
    ),
    KnowledgeArea(
        key="payment_terms",
        label_ru="оплата, договор, ЭДО и отсрочка",
        question_ru=(
            "Как принимаете оплату, работаете ли по договору, ЭДО и отсрочке?"
        ),
        triggers=(r"оплат", r"договор", r"эдо", r"отсроч", r"счет", r"сч[её]т"),
        context_markers=("оплата", "договор", "эдо", "отсроч", "счет", "счёт"),
        claim_patterns=(
            r"работаем\s+[^.?!]*(?:отсроч|эдо|договор)",
            r"есть\s+[^.?!]*(?:отсроч|эдо)",
        ),
    ),
    KnowledgeArea(
        key="samples",
        label_ru="образцы, каталог, КП и файлы",
        question_ru=(
            "Можно ли отправлять каталог/КП/образцы, в каком формате и кто это делает?"
        ),
        triggers=(r"образц", r"каталог", r"\bкп\b", r"pdf", r"презентац", r"файл"),
        context_markers=("образц", "каталог", "кп", "pdf", "презентац", "файл"),
        claim_patterns=(
            r"(?:пришлю|отправлю|прикреплю|выслал)[^.?!]*(?:каталог|кп|pdf|файл)",
            r"можем\s+привезти\s+образц",
        ),
    ),
    KnowledgeArea(
        key="address",
        label_ru="адрес, шоурум и визит",
        question_ru=(
            "Есть ли адрес/шоурум, можно ли приезжать и когда это уместно предлагать?"
        ),
        triggers=(r"адрес", r"где\s+вы", r"находитесь", r"приехать", r"шоурум"),
        context_markers=("адрес", "шоурум", "находимся", "приехать"),
        claim_patterns=(r"находимся\s+по\s+адрес", r"можно\s+приехать"),
    ),
)

HIGH_INTENT_PATTERNS = (
    r"\b\d{4,}\s*(?:штук|шт|стакан|единиц)",
    r"\b(?:тысяч|миллион|млн)\b[^.?!]*(?:штук|стакан)",
    r"\b\d+\s*(?:тысяч|млн)\b",
    r"к\s+(?:пятниц|понедельник|вторник|сред|четверг|суббот|воскрес)",
    r"срочн",
    r"оплата\s+от\s+юрлиц",
    r"готов\w*\s+заказ",
)

BASE_VERIFICATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "pricing": (
        r"(?:цен[аы]|стоимость|прайс)[^.?!]*(?:\d|руб|₽|\$|€)",
        r"(?:расценк|бюджет)[^.?!]*(?:\d|руб|₽|\$|€|usd|доллар)",
        r"минимальн\w*\s+заказ[^.?!]*\d",
        r"минимальн\w*\s+бюджет[^.?!]*\d",
    ),
    "delivery": (
        r"(?:доставк|доставляем|отгруз|срок)[^.?!]*"
        r"(?:\d|дн|час|рф|росси|москв|регион|самовывоз|склад|транспортн)",
    ),
    "assortment": (
        r"(?:ассортимент|размер|об[ъь]ем|материал|крышк)[^.?!]*"
        r"(?:\d|мл|см|мм|пластик|бумаж|био|горяч|холодн)",
        r"(?:только|не\s+прода[её]м)[^.?!]*(?:пластик|бумаж|био|крышк)",
    ),
    "branding": (
        r"(?:брендирован|логотип|печать|кастом)[^.?!]*"
        r"(?:возмож|делаем|наносим|минимальн|тираж|срок|\d)",
    ),
    "documents": (
        r"(?:сертификат|закрывающ\w*\s+документ|документ\w*\s+для\s+юрлиц)",
    ),
    "payment_terms": (
        r"(?:оплат|договор|эдо|отсроч|сч[её]т)[^.?!]*(?:есть|работаем|принимаем|\d|дн)",
    ),
    "samples": (
        r"(?:образц|каталог|кп|pdf|презентац|файл)[^.?!]*(?:есть|можем|отправ|пришл)",
    ),
    "address": (
        r"(?:адрес|шоурум|находимся|приехать)[^.?!]*(?:улиц|проспект|москв|офис|склад|\d)",
    ),
}


def _details_dict(script: Any | None) -> dict[str, Any]:
    details = getattr(script, "business_details", None) if script is not None else None
    return details if isinstance(details, dict) else {}


def _details_text(details: dict[str, Any]) -> str:
    chunks: list[str] = []
    answers = details.get("answers")
    if isinstance(answers, dict):
        for value in answers.values():
            if isinstance(value, str) and value.strip():
                chunks.append(value)
    notes = details.get("owner_notes")
    if isinstance(notes, list):
        for note in notes:
            if isinstance(note, dict):
                text = note.get("text")
                if isinstance(text, str) and text.strip():
                    chunks.append(text)
            elif isinstance(note, str) and note.strip():
                chunks.append(note)
    return collapse_whitespace(" ".join(chunks))


def _script_text(script: Any | None) -> str:
    if script is None:
        return ""
    parts = [
        getattr(script, "name", ""),
        getattr(script, "role_prompt", ""),
        getattr(script, "target_audience", ""),
        getattr(script, "goal", ""),
        getattr(script, "success_criteria", ""),
        getattr(script, "call_to_action", ""),
        _details_text(_details_dict(script)),
    ]
    return collapse_whitespace(" ".join(str(part or "") for part in parts)).lower()


def _matches_any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _answer_is_known(text: str) -> bool:
    lower = text.lower().strip()
    return bool(lower) and not any(marker in lower for marker in UNKNOWN_ANSWER_MARKERS)


def area_by_key(category: str) -> KnowledgeArea | None:
    for area in KNOWLEDGE_AREAS:
        if area.key == category:
            return area
    return None


def _base_text_verifies_area(category: str, text: str) -> bool:
    patterns = BASE_VERIFICATION_PATTERNS.get(category)
    return bool(patterns and _matches_any(patterns, text))


def has_verified_detail(script: Any | None, category: str) -> bool:
    """Return True when a category has explicit owner-provided context."""
    details = _details_dict(script)
    answers = details.get("answers")
    if isinstance(answers, dict):
        answer = answers.get(category)
        if isinstance(answer, str) and _answer_is_known(answer):
            return True

    area = area_by_key(category)
    details_text = _details_text(details).lower()
    if area and details_text:
        if any(marker in details_text for marker in area.context_markers):
            return True
    if area and script is not None:
        base_parts = [
            getattr(script, "role_prompt", ""),
            getattr(script, "target_audience", ""),
            getattr(script, "goal", ""),
            getattr(script, "success_criteria", ""),
            getattr(script, "call_to_action", ""),
        ]
        base_text = collapse_whitespace(
            " ".join(str(part or "") for part in base_parts)
        ).lower()
        return _base_text_verifies_area(area.key, base_text)
    return False


def verified_detail_excerpt(
    script: Any | None,
    category: str,
    *,
    max_chars: int = 260,
) -> str:
    """Return a short verified owner-provided excerpt for a business category."""
    details = _details_dict(script)
    answers = details.get("answers")
    if isinstance(answers, dict):
        answer = answers.get(category)
        if isinstance(answer, str) and _answer_is_known(answer):
            return sanitize_context_text(answer, max_chars=max_chars)

    text = _details_text(details)
    if not text:
        return ""

    if category == "pricing":
        sentence_pattern = (
            r"[^.?!]*(?:цен|стоим|прайс|расцен|бюджет|скидк|"
            r"минимальн\w*\s+(?:бюджет|заказ))[^.?!]*"
            r"(?:\d|руб|₽|\$|€|usd|доллар)[^.?!]*[.?!]?"
        )
        matches = [
            collapse_whitespace(match).strip(" ,;")
            for match in re.findall(sentence_pattern, text, flags=re.IGNORECASE)
        ]
        for match in matches:
            if match:
                return sanitize_context_text(match, max_chars=max_chars)

    area = area_by_key(category)
    if area:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            lower = sentence.lower()
            if any(marker in lower for marker in area.context_markers):
                return sanitize_context_text(sentence, max_chars=max_chars)
    return ""


def detect_clarification_need(script: Any | None, lead_text: str) -> KnowledgeArea | None:
    """Return the first missing verified-fact area requested by a lead."""
    lower = collapse_whitespace(lead_text).lower()
    if not lower:
        return None
    for area in KNOWLEDGE_AREAS:
        if _matches_any(area.triggers, lower) and not has_verified_detail(script, area.key):
            return area
    return None


def detect_unsupported_claim(script: Any | None, response_text: str) -> KnowledgeArea | None:
    """Return an area when a generated response claims a fact we do not know."""
    lower = collapse_whitespace(response_text).lower()
    if not lower:
        return None
    for area in KNOWLEDGE_AREAS:
        if has_verified_detail(script, area.key):
            continue
        if area.claim_patterns and _matches_any(area.claim_patterns, lower):
            return area
    return None


def looks_like_high_commercial_intent(lead_text: str) -> bool:
    """Detect purchase intent that should be handed to a human even without a call ask."""
    lower = collapse_whitespace(lead_text).lower()
    return _matches_any(HIGH_INTENT_PATTERNS, lower)


def missing_business_context_questions(script: Any | None, limit: int = 8) -> list[KnowledgeArea]:
    """Return important missing business facts to ask the owner before launch."""
    missing: list[KnowledgeArea] = []
    for area in KNOWLEDGE_AREAS:
        if has_verified_detail(script, area.key):
            continue
        missing.append(area)
    return missing[:limit]


def _audit_business_phrase(script: Any | None) -> str:
    if script is None:
        return "этого бизнеса"
    for field in ("role_prompt", "name", "goal", "target_audience"):
        text = sanitize_context_text(getattr(script, field, ""), max_chars=140)
        if text and not text.startswith("["):
            return text.strip(" .")
    return "этого бизнеса"


def _audit_draft_lines(script: Any | None) -> list[str]:
    if script is None:
        return []
    fields = (
        ("Название", "name"),
        ("Описание/роль менеджера", "role_prompt"),
        ("Аудитория", "target_audience"),
        ("Цель диалога", "goal"),
        ("Критерий успеха", "success_criteria"),
        ("Следующий шаг", "call_to_action"),
    )
    lines: list[str] = []
    for label, attr in fields:
        value = sanitize_context_text(getattr(script, attr, ""), max_chars=700)
        if value:
            lines.append(f"{label}: {value}")
    details_text = _details_text(_details_dict(script))
    if details_text:
        lines.append(
            "Уже подтвержденные факты владельца: "
            + sanitize_context_text(details_text, max_chars=900)
        )
    return lines


def build_business_audit_messages(
    script: Any | None,
    *,
    lang: str = "ru",
) -> list[dict[str, str]]:
    """Build an LLM prompt for business-specific pre-launch clarification questions."""
    response_language = "English" if lang == "en" else "Russian"
    draft = "\n".join(_audit_draft_lines(script)) or "Черновик почти пустой."
    return [
        {
            "role": "system",
            "content": (
                "Ты аналитик внедрения AI sales manager. Твоя задача - найти "
                "конкретные пробелы в черновике бизнеса, из-за которых AI-менеджер "
                "может начать додумывать факты в переписке с лидами. "
                "Задавай вопросы владельцу бизнеса, а не лиду. "
                "Не спрашивай то, что уже явно указано в черновике. "
                "Не используй общие вопросы вроде 'какие цены?' без привязки "
                "к продукту, аудитории или сценарию продажи. "
                "Верни только JSON без markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Language for questions: {response_language}.\n\n"
                "Черновик бизнеса:\n"
                f"{draft}\n\n"
                "Сформулируй от 3 до 6 самых важных уточняющих вопросов. "
                "Каждый вопрос должен быть точным для этого бизнеса: упоминай "
                "продукт, аудиторию, тип сделки, ограничение или ситуацию лида, "
                "если это следует из черновика. "
                "Фокус: факты, которые AI-менеджеру опасно выдумывать "
                "(условия, цены, ограничения, сроки, документы, следующий шаг, "
                "что нельзя обещать). "
                'Формат ответа: {"questions":["...","..."]}'
            ),
        },
    ]


def _coerce_question_items(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        questions = raw.get("questions")
        return questions if isinstance(questions, list) else []
    if isinstance(raw, str):
        return [raw]
    return []


def _json_questions_from_text(text: str) -> list[Any]:
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```$", "", stripped)
    candidates = [stripped]
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match and match.group(0) != stripped:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        items = _coerce_question_items(parsed)
        if items:
            return items
    return []


def _normalize_audit_question(value: Any) -> str:
    text = sanitize_context_text(value, max_chars=260)
    if not text or text.startswith("["):
        return ""
    text = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", text)
    text = text.strip(" \t\r\n\"'«»")
    text = collapse_whitespace(text)
    if len(text) < 18:
        return ""
    question_index = text.find("?")
    if question_index >= 0:
        text = text[: question_index + 1]
    else:
        text = text.rstrip(".!;:") + "?"
    return text


def _is_overly_generic_audit_question(question: str) -> bool:
    normalized = question.lower().strip(" ?!.")
    generic_exact = {
        "какие цены",
        "какая цена",
        "какие сроки",
        "какая аудитория",
        "какие условия",
        "что продаете",
        "что вы продаете",
        "какие преимущества",
        "what are the prices",
        "what are the terms",
        "who is the audience",
    }
    return normalized in generic_exact


def normalize_business_audit_questions(
    raw: Any,
    *,
    limit: int = AUDIT_QUESTION_LIMIT,
) -> list[str]:
    """Normalize LLM/fallback audit questions into concise owner-facing questions."""
    items = _coerce_question_items(raw)
    if isinstance(raw, str):
        json_items = _json_questions_from_text(raw)
        if json_items:
            items = json_items
        else:
            items = raw.splitlines()

    questions: list[str] = []
    seen: set[str] = set()
    for item in items:
        question = _normalize_audit_question(item)
        if not question or _is_overly_generic_audit_question(question):
            continue
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        questions.append(question)
        if len(questions) >= limit:
            break
    return questions


def parse_business_audit_questions(
    text: str,
    *,
    limit: int = AUDIT_QUESTION_LIMIT,
) -> list[str]:
    """Parse an LLM audit response into owner clarification questions."""
    return normalize_business_audit_questions(text, limit=limit)


def fallback_business_context_questions(
    script: Any | None,
    *,
    limit: int = AUDIT_QUESTION_LIMIT,
) -> list[str]:
    """Return deterministic business-tied questions when LLM audit is unavailable."""
    business = _audit_business_phrase(script)
    templates = {
        "pricing": (
            f"Какой минимальный заказ, ценовой диапазон и правила скидок можно "
            f"уверенно называть по направлению «{business}»?"
        ),
        "delivery": (
            f"Какие сроки, регионы доставки и ограничения по срочности важны "
            f"для клиентов в оффере «{business}»?"
        ),
        "assortment": (
            f"Какие варианты продукта, материалы, размеры или комплектации есть "
            f"в оффере «{business}», а чего точно нет?"
        ),
        "branding": (
            f"Если лид попросит кастомизацию или логотип по офферу «{business}», "
            "какие условия, сроки и минимальные тиражи можно обещать?"
        ),
        "documents": (
            f"Какие сертификаты, договоры или закрывающие документы можно "
            f"предлагать клиентам по офферу «{business}»?"
        ),
        "payment_terms": (
            f"Какие способы оплаты, договор, ЭДО или отсрочку можно обсуждать "
            f"с лидами по офферу «{business}»?"
        ),
        "samples": (
            f"Какие материалы можно отправлять лиду по офферу «{business}»: "
            "каталог, КП, образцы, презентацию?"
        ),
        "address": (
            f"Есть ли адрес, шоурум или склад, куда уместно приглашать лида "
            f"по офферу «{business}»?"
        ),
    }
    questions: list[str] = []
    for area in missing_business_context_questions(script, limit=limit):
        question = templates.get(area.key, area.question_ru)
        questions.append(question)
    return normalize_business_audit_questions(questions, limit=limit)


def audit_questions_from_details(
    details: dict[str, Any] | None,
    *,
    limit: int = AUDIT_QUESTION_LIMIT,
) -> list[str]:
    current = details if isinstance(details, dict) else {}
    audit = current.get("audit")
    audit = audit if isinstance(audit, dict) else {}
    return normalize_business_audit_questions(audit.get("questions"), limit=limit)


def store_audit_questions(
    details: dict[str, Any] | None,
    questions: list[str],
    *,
    source: str = "llm",
) -> dict[str, Any]:
    current = dict(details or {})
    audit = dict(current.get("audit") or {})
    normalized = normalize_business_audit_questions(questions)
    audit["questions"] = normalized
    audit["source"] = sanitize_context_text(source, max_chars=80) or "llm"
    audit["generated_at"] = datetime.now(timezone.utc).isoformat()
    audit.pop("skipped_at", None)
    current["audit"] = audit
    return current


def merge_owner_answer(
    details: dict[str, Any] | None,
    answer: str,
    *,
    category: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    """Store owner-provided facts without mixing them into lead message history."""
    current = dict(details or {})
    answers = dict(current.get("answers") or {})
    notes = list(current.get("owner_notes") or [])
    cleaned = sanitize_context_text(answer, max_chars=1600)
    if not cleaned:
        return current

    now = datetime.now(timezone.utc).isoformat()
    if category:
        answers[category] = cleaned
    notes.append(
        {
            "category": category or "general",
            "question": sanitize_context_text(question or "", max_chars=500),
            "text": cleaned,
            "added_at": now,
        }
    )
    current["answers"] = answers
    current["owner_notes"] = notes[-20:]
    current["last_updated_at"] = now
    return current


def mark_audit_skipped(details: dict[str, Any] | None) -> dict[str, Any]:
    current = dict(details or {})
    audit = dict(current.get("audit") or {})
    audit["skipped_at"] = datetime.now(timezone.utc).isoformat()
    current["audit"] = audit
    return current


def mark_audit_answered(details: dict[str, Any] | None) -> dict[str, Any]:
    current = dict(details or {})
    audit = dict(current.get("audit") or {})
    audit["answered_at"] = datetime.now(timezone.utc).isoformat()
    current["audit"] = audit
    return current


def business_audit_has_owner_answer(details: dict[str, Any] | None) -> bool:
    current = details if isinstance(details, dict) else {}
    audit = current.get("audit")
    audit = audit if isinstance(audit, dict) else {}
    if audit.get("answered_at"):
        return True
    notes = current.get("owner_notes")
    return isinstance(notes, list) and bool(notes)


def business_details_prompt_block(script: Any | None) -> str:
    """Format owner-provided business facts for LLM grounding."""
    details = _details_dict(script)
    answers = details.get("answers")
    notes = details.get("owner_notes")
    lines: list[str] = []

    if isinstance(answers, dict):
        for category, value in answers.items():
            if not isinstance(value, str) or not _answer_is_known(value):
                continue
            area = area_by_key(str(category))
            label = area.label_ru if area else str(category)
            safe_value = sanitize_context_text(value, max_chars=400)
            if safe_value:
                lines.append(f"- {label}: {safe_value}")

    if not lines and isinstance(notes, list):
        for note in notes[-5:]:
            text = note.get("text") if isinstance(note, dict) else note
            safe_text = sanitize_context_text(text, max_chars=400)
            if safe_text:
                lines.append(f"- Уточнение владельца: {safe_text}")

    return "\n".join(lines)


def lead_hold_message(area: KnowledgeArea) -> str:
    return (
        f"Уточню {area.label_ru}, чтобы не обещать наугад. "
        "Вернусь с точным ответом."
    )


def safe_unknown_fact_reply(area: KnowledgeArea) -> str:
    return (
        f"По теме «{area.label_ru}» не буду обещать без проверки. "
        "Лучше сверить этот момент отдельно, чтобы не назвать неверные условия."
    )
