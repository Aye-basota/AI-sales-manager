"""Lead discovery through Telegram MTProto global message search.

The MVP uses the official Telegram account API through Pyrogram's
``Client.search_global`` wrapper around MTProto global message search. It does
not depend on a paid directory API.
"""

from __future__ import annotations

import inspect
import logging
import re
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


COUNTRY_CODES = {
    "poland": "pl",
    "польша": "pl",
    "polska": "pl",
    "russia": "ru",
    "россия": "ru",
    "germany": "de",
    "германия": "de",
    "deutschland": "de",
    "usa": "us",
    "united states": "us",
    "сша": "us",
    "uk": "gb",
    "united kingdom": "gb",
    "великобритания": "gb",
}
COUNTRY_EN_NAMES = {
    "pl": "Poland",
    "ru": "Russia",
    "de": "Germany",
    "us": "United States",
    "gb": "United Kingdom",
}
LANGUAGE_CODES = {
    "polish": "pl",
    "польский": "pl",
    "polski": "pl",
    "english": "en",
    "английский": "en",
    "russian": "ru",
    "русский": "ru",
    "german": "de",
    "немецкий": "de",
}
NEED_PATTERNS = (
    "ищем",
    "ищу",
    "посоветуйте",
    "нужен",
    "нужна",
    "нужно",
    "подрядчик",
    "автоматиза",
    "crm",
    "erp",
    "wms",
    "integracja",
    "automatyzacja",
    "szukam",
    "polecacie",
    "potrzeb",
    "recommend",
    "looking for",
    "need",
    "vendor",
    "contractor",
)
LOW_VALUE_PATTERNS = (
    "ваканси",
    "работа",
    "резюме",
    "job",
    "jobs",
    "hiring",
    "реклама",
    "скидк",
    "promo",
    "casino",
    "crypto signal",
    "giveaway",
)


@dataclass
class TelegramGlobalSearchCriteria:
    business_description: str
    audience_description: str
    country: str
    language: str
    pain_keywords: str = ""
    limit: int = 50
    messages_per_query: int = 40
    recent_days: int = 30


@dataclass
class TelegramGlobalSearchResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    posts_checked: int = 0
    errors: list[str] = field(default_factory=list)


def _normalize_code(value: str, mapping: dict[str, str]) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    return mapping.get(raw, raw[:2] if len(raw) == 2 else raw)


def normalize_country(value: str) -> str:
    return _normalize_code(value, COUNTRY_CODES)


def normalize_language(value: str) -> str:
    return _normalize_code(value, LANGUAGE_CODES)


def _country_english_name(value: str) -> str:
    code = normalize_country(value)
    return COUNTRY_EN_NAMES.get(code, value.strip())


def _compact(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _keyword_tokens(*parts: str) -> list[str]:
    text = " ".join(parts).lower()
    tokens = re.findall(r"[\wąćęłńóśźżа-яё-]{3,}", text, flags=re.IGNORECASE)
    stop = {
        "для",
        "что",
        "как",
        "the",
        "and",
        "with",
        "from",
        "company",
        "business",
        "owner",
        "owners",
        "директор",
        "владелец",
    }
    result: list[str] = []
    for token in tokens:
        if token in stop or token in result:
            continue
        result.append(token)
    return result[:18]


def _local_query_expansions(criteria: TelegramGlobalSearchCriteria) -> list[str]:
    text = " ".join(
        [
            criteria.business_description,
            criteria.audience_description,
            criteria.country,
            criteria.language,
            criteria.pain_keywords,
        ]
    ).lower()
    country_name = _country_english_name(criteria.country)
    country_code = normalize_country(criteria.country)
    language_code = normalize_language(criteria.language)
    queries: list[str] = []

    if (
        country_code == "pl"
        or language_code == "pl"
        or "poland" in text
        or "polska" in text
    ):
        queries.extend(
            [
                "logistyka",
                "spedycja",
                "firmy transportowe",
                "właściciele firm transportowych",
                "3PL",
                "freight forwarding",
                f"transport business {country_name}",
            ]
        )

    return queries


def build_telegram_global_queries(
    criteria: TelegramGlobalSearchCriteria,
) -> list[str]:
    """Build local-language and English queries for Telegram global search."""
    audience = criteria.audience_description
    country = criteria.country
    country_name_en = _country_english_name(country)
    pains = criteria.pain_keywords
    tokens = _keyword_tokens(audience, country, pains)
    queries: list[str] = _local_query_expansions(criteria)

    for token in tokens[:8]:
        queries.append(token)

    combined = [
        audience,
        f"{audience} {country}",
        f"{audience} {pains}".strip(),
        f"{pains} {country}".strip(),
    ]
    for query in combined:
        query = _compact(query, 90)
        if query:
            queries.append(query)

    for need in ("CRM", "ERP", "automation", "vendor", "contractor"):
        if country:
            queries.append(f"{need} {country}")
            if country_name_en and country_name_en.lower() != country.lower():
                queries.append(f"{need} {country_name_en}")
        else:
            queries.append(need)

    unique: list[str] = []
    for query in queries:
        query = " ".join(query.split())
        if len(query) < 3:
            continue
        if query.lower() not in {item.lower() for item in unique}:
            unique.append(query)
    return unique[:24]


def _is_low_value(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in LOW_VALUE_PATTERNS)


def _is_relevant_text(text: str, criteria: TelegramGlobalSearchCriteria) -> bool:
    lower = text.lower()
    if _is_low_value(lower):
        return False
    tokens = _keyword_tokens(
        criteria.business_description,
        criteria.audience_description,
        criteria.country,
        criteria.pain_keywords,
    )
    return any(token.lower() in lower for token in tokens) or any(
        pattern in lower for pattern in NEED_PATTERNS
    )


def _message_text(message: Any) -> str:
    return (
        getattr(message, "text", None)
        or getattr(message, "caption", None)
        or getattr(message, "message", None)
        or ""
    )


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return str(value or "")


def _is_recent_message(message: Any, recent_days: int) -> bool:
    value = getattr(message, "date", None)
    if not isinstance(value, datetime):
        return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - value <= timedelta(days=recent_days)


def _chat_type_name(chat: Any) -> str:
    chat_type = getattr(chat, "type", "")
    return str(getattr(chat_type, "value", chat_type) or "").lower()


def _is_public_group_like_message(message: Any) -> bool:
    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)
    if not chat or not user:
        return False
    chat_type = _chat_type_name(chat)
    if "private" in chat_type or "bot" in chat_type:
        return False
    if getattr(user, "is_bot", False) or getattr(user, "is_deleted", False):
        return False
    return True


def _message_link(message: Any) -> str:
    chat = getattr(message, "chat", None)
    username = getattr(chat, "username", None)
    message_id = getattr(message, "id", None)
    if username and message_id:
        return f"https://t.me/{str(username).lstrip('@')}/{message_id}"
    return ""


def _chat_title(chat: Any) -> str:
    return (
        getattr(chat, "title", None)
        or getattr(chat, "username", None)
        or getattr(chat, "first_name", None)
        or "public Telegram chat"
    )


def _chat_group_record(chat: Any) -> dict[str, Any]:
    return {
        "id": getattr(chat, "id", None),
        "title": _chat_title(chat),
        "username": getattr(chat, "username", None),
        "type": _chat_type_name(chat),
    }


def _group_key(chat: Any) -> str:
    return str(
        getattr(chat, "id", None)
        or getattr(chat, "username", None)
        or _chat_title(chat)
    ).lower()


def _contact_record_from_message(
    message: Any,
    criteria: TelegramGlobalSearchCriteria,
) -> dict[str, Any] | None:
    user = getattr(message, "from_user", None)
    if not user:
        return None
    user_id = getattr(user, "id", None)
    username = getattr(user, "username", None)
    if not user_id and not username:
        return None

    text = _message_text(message)
    chat = getattr(message, "chat", None)
    chat_title = _chat_title(chat)
    summary = f"Telegram global search: {chat_title}. Message: {_compact(text, 150)}"

    return {
        "telegram_user_id": user_id,
        "telegram_username": username,
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "company_name": "",
        "position": "",
        "city": criteria.country,
        "industry": _compact(criteria.audience_description, 100),
        "source": "telegram_search",
        "last_source": "telegram_search",
        "source_url": _message_link(message),
        "source_summary": summary,
        "source_message_text": _compact(text, 900),
        "source_message_date": _format_date(getattr(message, "date", None)),
        "is_valid": "unknown",
        "icp_score": 80,
    }


async def _iterate_result_items(result: Any) -> AsyncIterator[Any]:
    if inspect.isawaitable(result):
        result = await result
    if result is None:
        return
    if hasattr(result, "__aiter__"):
        async for item in result:
            yield item
        return
    if isinstance(result, Iterable) and not isinstance(result, (str, bytes, dict)):
        for item in result:
            yield item
        return
    yield result


class TelegramGlobalLeadSearch:
    """Search public Telegram messages and return visible authors as leads."""

    async def _search_global_messages(
        self,
        telegram_client: Any,
        query: str,
        limit: int,
    ) -> AsyncIterator[Any]:
        try:
            result = telegram_client.search_global(query=query, limit=limit)
        except TypeError:
            result = telegram_client.search_global(q=query, limit=limit)

        async for item in _iterate_result_items(result):
            yield item

    async def run(
        self,
        criteria: TelegramGlobalSearchCriteria,
        *,
        telegram_client: Any,
    ) -> TelegramGlobalSearchResult:
        queries = build_telegram_global_queries(criteria)
        result = TelegramGlobalSearchResult(queries=queries)
        records_by_key: dict[str, dict[str, Any]] = {}
        groups_by_key: dict[str, dict[str, Any]] = {}

        for query in queries:
            if len(records_by_key) >= criteria.limit:
                break
            try:
                async for message in self._search_global_messages(
                    telegram_client,
                    query,
                    limit=criteria.messages_per_query,
                ):
                    result.posts_checked += 1
                    if len(records_by_key) >= criteria.limit:
                        break
                    text = _message_text(message)
                    if not text:
                        continue
                    if not _is_recent_message(message, criteria.recent_days):
                        continue
                    if not _is_public_group_like_message(message):
                        continue
                    if not _is_relevant_text(text, criteria):
                        continue

                    chat = getattr(message, "chat", None)
                    if chat is not None:
                        groups_by_key.setdefault(_group_key(chat), _chat_group_record(chat))

                    record = _contact_record_from_message(message, criteria)
                    if not record:
                        continue
                    key = str(
                        record.get("telegram_user_id")
                        or record.get("telegram_username")
                        or ""
                    ).lower()
                    if key:
                        records_by_key.setdefault(key, record)
            except Exception as exc:
                logger.warning("Telegram global search failed for %r: %s", query, exc)
                result.errors.append(f"{query}: {exc}")

        result.groups = list(groups_by_key.values())
        result.records = list(records_by_key.values())[: criteria.limit]
        return result
