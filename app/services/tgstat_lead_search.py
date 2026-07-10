"""TGStat-based lead discovery for public Telegram chats.

TGStat is used to find relevant public chats and posts. A connected Telegram
user account is then used to resolve visible message authors into importable
contacts. TGStat itself is not treated as a user ID database.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import get_settings

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
class TgstatLeadSearchCriteria:
    business_description: str
    audience_description: str
    country: str
    language: str
    pain_keywords: str = ""
    limit: int = 50
    groups_limit: int = 20
    posts_per_query: int = 30


@dataclass
class TgstatLeadSearchResult:
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


def _local_query_expansions(criteria: TgstatLeadSearchCriteria) -> list[str]:
    """Return small, deterministic local/English query expansions for common ICPs."""
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
        or any(token in text for token in ("logist", "transport", "spedycj", "3pl"))
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


def _compact(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


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


def build_tgstat_queries(criteria: TgstatLeadSearchCriteria) -> list[str]:
    """Build country-language and English TGStat queries from ICP text."""
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
        if query and query.lower() not in {q.lower() for q in queries}:
            queries.append(query)

    # Generic B2B-need searches catch people asking for tools/vendors even when
    # their profile text is sparse.
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
        if query.lower() not in {q.lower() for q in unique}:
            unique.append(query)
    return unique[:24]


def _response_items(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    response = data.get("response", data)
    if isinstance(response, dict):
        items = response.get("items") or response.get("channels") or response.get("posts")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    return []


def _item_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("title"),
        item.get("about"),
        item.get("description"),
        item.get("text"),
        item.get("message"),
    ]
    channel = item.get("channel")
    if isinstance(channel, dict):
        parts.extend([channel.get("title"), channel.get("about"), channel.get("username")])
    return " ".join(str(part or "") for part in parts).lower()


def _is_low_value(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in LOW_VALUE_PATTERNS)


def _is_relevant_text(text: str, criteria: TgstatLeadSearchCriteria) -> bool:
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


def _channel_link(item: dict[str, Any]) -> str:
    for key in ("link", "url", "invite_link"):
        if item.get(key):
            return str(item[key])
    username = item.get("username")
    if username:
        return f"https://t.me/{str(username).lstrip('@')}"
    return ""


def _post_link(item: dict[str, Any]) -> str:
    for key in ("link", "url", "postLink"):
        if item.get(key):
            return str(item[key])
    channel = item.get("channel")
    if isinstance(channel, dict):
        username = channel.get("username")
        message_id = item.get("id") or item.get("message_id")
        if username and message_id:
            return f"https://t.me/{str(username).lstrip('@')}/{message_id}"
    return ""


def _channel_username_from_item(item: dict[str, Any]) -> str:
    username = item.get("username")
    if username:
        return str(username).lstrip("@")
    link = _channel_link(item)
    if not link:
        return ""
    parsed = urlparse(link if "://" in link else f"https://{link}")
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0] not in {"c", "s"}:
        return parts[0]
    return ""


def _parse_public_message_link(link: str) -> tuple[str, int] | None:
    if not link:
        return None
    parsed = urlparse(link if "://" in link else f"https://{link}")
    if "t.me" not in parsed.netloc:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] in {"c", "s"}:
        return None
    try:
        return parts[0], int(parts[1])
    except ValueError:
        return None


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return str(value or "")


def _contact_record_from_message(
    user: Any,
    text: str,
    link: str,
    message_date: Any,
    criteria: TgstatLeadSearchCriteria,
    chat_title: str = "",
) -> dict[str, Any] | None:
    if not user:
        return None
    username = getattr(user, "username", None)
    user_id = getattr(user, "id", None)
    if not username and not user_id:
        return None
    summary = f"TGStat: {chat_title or 'public Telegram chat'}. Message: {_compact(text, 150)}"
    return {
        "telegram_user_id": user_id,
        "telegram_username": username,
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "company_name": "",
        "position": "",
        "city": criteria.country,
        "industry": _compact(criteria.audience_description, 100),
        "source": "tgstat",
        "last_source": "tgstat",
        "source_url": link,
        "source_summary": summary,
        "source_message_text": _compact(text, 900),
        "source_message_date": _format_date(message_date),
        "is_valid": "unknown",
    }


class TGStatLeadSearch:
    """Search TGStat and resolve visible Telegram message authors."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.token = token if token is not None else settings.tgstat_token
        self.base_url = (base_url or settings.tgstat_base_url).rstrip("/")
        self.timeout_s = timeout_s

    @property
    def configured(self) -> bool:
        return bool(self.token)

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError("TGSTAT_TOKEN is not configured")
        clean_params = {k: v for k, v in params.items() if v not in (None, "")}
        clean_params["token"] = self.token
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.get(f"{self.base_url}{path}", params=clean_params)
            response.raise_for_status()
            data = response.json()
        if isinstance(data, dict) and data.get("ok") is False:
            raise RuntimeError(str(data.get("error") or data))
        return data if isinstance(data, dict) else {}

    async def search_chats(
        self,
        query: str,
        *,
        country: str = "",
        language: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "/channels/search",
            {
                "q": query,
                "peer_type": "chat",
                "country": country,
                "language": language,
                "search_by_description": 1,
                "limit": limit,
            },
        )
        items = _response_items(data)
        return [item for item in items if "chat" in str(item.get("peer_type", "chat")).lower()]

    async def search_posts(
        self,
        query: str,
        *,
        country: str = "",
        language: str = "",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        start_date = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
        data = await self._get(
            "/posts/search",
            {
                "q": query,
                "peerType": "chat",
                "country": country,
                "language": language,
                "startDate": start_date,
                "limit": limit,
                "extended": 1,
                "hideForwards": 1,
                "hideDeleted": 1,
            },
        )
        return _response_items(data)

    async def run(
        self,
        criteria: TgstatLeadSearchCriteria,
        *,
        telegram_client: Any | None = None,
    ) -> TgstatLeadSearchResult:
        country = normalize_country(criteria.country)
        language = normalize_language(criteria.language)
        queries = build_tgstat_queries(criteria)
        result = TgstatLeadSearchResult(queries=queries)
        groups_by_username: dict[str, dict[str, Any]] = {}
        posts: list[dict[str, Any]] = []

        for query in queries:
            try:
                for group in await self.search_chats(
                    query,
                    country=country,
                    language=language,
                    limit=criteria.groups_limit,
                ):
                    text = _item_text(group)
                    username = _channel_username_from_item(group)
                    if username and _is_relevant_text(text, criteria):
                        groups_by_username.setdefault(username.lower(), group)
            except Exception as exc:
                logger.warning("TGStat chat search failed for %r: %s", query, exc)
                result.errors.append(f"chat:{query}: {exc}")

            try:
                query_posts = await self.search_posts(
                    query,
                    country=country,
                    language=language,
                    limit=criteria.posts_per_query,
                )
                result.posts_checked += len(query_posts)
                for post in query_posts:
                    text = _item_text(post)
                    if _is_relevant_text(text, criteria):
                        posts.append(post)
                        channel = post.get("channel")
                        if isinstance(channel, dict):
                            username = _channel_username_from_item(channel)
                            if username:
                                groups_by_username.setdefault(username.lower(), channel)
            except Exception as exc:
                logger.warning("TGStat post search failed for %r: %s", query, exc)
                result.errors.append(f"post:{query}: {exc}")

        result.groups = list(groups_by_username.values())[: criteria.groups_limit]
        if telegram_client is None:
            return result

        records_by_key: dict[str, dict[str, Any]] = {}
        for post in posts:
            if len(records_by_key) >= criteria.limit:
                break
            record = await self._record_from_tgstat_post(post, criteria, telegram_client)
            if record:
                key = str(record.get("telegram_user_id") or record.get("telegram_username") or "")
                if key:
                    records_by_key.setdefault(key.lower(), record)

        if len(records_by_key) < criteria.limit:
            for group in result.groups:
                if len(records_by_key) >= criteria.limit:
                    break
                async for record in self._records_from_group_history(
                    group,
                    criteria,
                    telegram_client,
                    remaining=criteria.limit - len(records_by_key),
                ):
                    key = str(record.get("telegram_user_id") or record.get("telegram_username") or "")
                    if key:
                        records_by_key.setdefault(key.lower(), record)

        result.records = list(records_by_key.values())[: criteria.limit]
        return result

    async def _record_from_tgstat_post(
        self,
        post: dict[str, Any],
        criteria: TgstatLeadSearchCriteria,
        telegram_client: Any,
    ) -> dict[str, Any] | None:
        link = _post_link(post)
        parsed = _parse_public_message_link(link)
        if not parsed:
            return None
        chat_username, message_id = parsed
        try:
            message = await telegram_client.get_messages(chat_username, message_id)
        except Exception as exc:
            logger.debug("Could not fetch Telegram message %s: %s", link, exc)
            return None
        text = getattr(message, "text", None) or getattr(message, "caption", None) or _item_text(post)
        if not _is_relevant_text(text, criteria):
            return None
        chat = getattr(message, "chat", None)
        chat_title = getattr(chat, "title", "") or chat_username
        return _contact_record_from_message(
            getattr(message, "from_user", None),
            text,
            link,
            getattr(message, "date", None) or post.get("date"),
            criteria,
            chat_title,
        )

    async def _records_from_group_history(
        self,
        group: dict[str, Any],
        criteria: TgstatLeadSearchCriteria,
        telegram_client: Any,
        *,
        remaining: int,
    ):
        username = _channel_username_from_item(group)
        if not username:
            return
        chat_title = str(group.get("title") or username)
        link_prefix = f"https://t.me/{username}"
        checked = 0
        try:
            async for message in telegram_client.get_chat_history(username, limit=120):
                if checked >= 120 or remaining <= 0:
                    break
                checked += 1
                text = getattr(message, "text", None) or getattr(message, "caption", None) or ""
                if not text or not _is_relevant_text(text, criteria):
                    continue
                message_id = getattr(message, "id", None)
                link = f"{link_prefix}/{message_id}" if message_id else link_prefix
                record = _contact_record_from_message(
                    getattr(message, "from_user", None),
                    text,
                    link,
                    getattr(message, "date", None),
                    criteria,
                    chat_title,
                )
                if record:
                    remaining -= 1
                    yield record
        except Exception as exc:
            logger.debug("Could not scan Telegram group %s: %s", username, exc)
