"""Lead discovery adapters for Telegram and external sources."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

try:
    import asyncio

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        _tmp_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_tmp_loop)

    from pyrogram import Client
    from pyrogram.types import User, ChatMember

    _PYROGRAM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYROGRAM_AVAILABLE = False


@dataclass
class LeadCriteria:
    """Search criteria for lead discovery."""

    query: str = ""
    limit: int = 20
    job_title: str = ""
    company: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class DiscoveredContact:
    """Lightweight contact representation from discovery sources."""

    telegram_username: str | None = None
    telegram_user_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    company_name: str | None = None
    position: str | None = None
    city: str | None = None
    industry: str | None = None
    bio: str | None = None
    source: str = "unknown"


class ExternalLeadSource(ABC):
    """Abstract adapter for external lead sources."""

    @abstractmethod
    async def search(self, criteria: LeadCriteria) -> List[DiscoveredContact]:
        """Search for leads using the provided criteria."""
        ...


class GenericJSONAdapter(ExternalLeadSource):
    """Generic adapter for external JSON APIs (e.g. Rosprofile)."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_url = api_url or os.getenv("EXTERNAL_LEAD_API_URL", "")
        self.api_key = api_key or os.getenv("EXTERNAL_LEAD_API_KEY", "")

    async def search(self, criteria: LeadCriteria) -> List[DiscoveredContact]:
        if not self.api_url:
            return []

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        params: dict[str, Any] = {"q": criteria.query, "limit": criteria.limit}
        if criteria.job_title:
            params["job_title"] = criteria.job_title
        if criteria.company:
            params["company"] = criteria.company

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.api_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.warning("External lead API request failed: %s", exc)
            return []

        results: List[DiscoveredContact] = []
        for item in data if isinstance(data, list) else data.get("results", []):
            if not isinstance(item, dict):
                continue
            contact = DiscoveredContact(
                telegram_username=item.get("telegram_username") or item.get("username"),
                telegram_user_id=item.get("telegram_user_id") or item.get("user_id"),
                first_name=item.get("first_name"),
                last_name=item.get("last_name"),
                phone=item.get("phone"),
                company_name=item.get("company_name") or item.get("company"),
                position=item.get("position") or item.get("job_title"),
                city=item.get("city"),
                industry=item.get("industry"),
                source="external_api",
            )
            results.append(contact)

        return results


class RosprofileAdapter(GenericJSONAdapter):
    """Rosprofile-specific adapter (currently a thin wrapper around GenericJSONAdapter)."""

    async def search(self, criteria: LeadCriteria) -> List[DiscoveredContact]:
        if not self.api_url:
            raise NotImplementedError(
                "Rosprofile integration requires EXTERNAL_LEAD_API_URL and EXTERNAL_LEAD_API_KEY in .env"
            )
        return await super().search(criteria)


class TelegramPublicSearch:
    """Search public Telegram users via Pyrogram global search."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    async def search(
        self, query: str, limit: int = 20
    ) -> List[DiscoveredContact]:
        """Search Telegram globally for users matching *query*.

        If a Pyrogram *client* was provided at init, it is used directly.
        Otherwise the function attempts to build a temporary client from
        environment settings (best-effort).
        """
        if not _PYROGRAM_AVAILABLE:
            logger.warning("Pyrogram not available, cannot search Telegram public")
            return []

        results: List[DiscoveredContact] = []
        client = self._client
        temporary_client = False

        if client is None:
            settings = get_settings()
            if settings.telegram_api_id and settings.telegram_api_hash:
                client = Client(
                    name="lead_discovery",
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    in_memory=True,
                )
                temporary_client = True
                await client.start()

        if client is None:
            logger.warning("No Telegram client available for public search")
            return []

        try:
            # Pyrogram search_global returns chats/messages; we attempt to
            # extract user references from the result set.
            search_results = await client.search_global(q=query, limit=limit)
            usernames_seen: set[str] = set()

            for item in search_results:
                user: User | None = None
                if hasattr(item, "from_user") and item.from_user:
                    user = item.from_user
                elif hasattr(item, "user") and item.user:
                    user = item.user
                elif isinstance(item, User):
                    user = item

                if not user:
                    continue

                username = user.username
                if not username or username.lower() in usernames_seen:
                    continue
                usernames_seen.add(username.lower())

                results.append(
                    DiscoveredContact(
                        telegram_username=username,
                        telegram_user_id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        source="telegram_search",
                    )
                )

                if len(results) >= limit:
                    break
        except Exception as exc:
            logger.warning("Telegram public search failed: %s", exc)
        finally:
            if temporary_client:
                try:
                    await client.stop()
                except Exception:
                    logger.warning("Failed to stop lead discovery client", exc_info=True)

        return results


class ChannelMembersParser:
    """Parse members from a Telegram channel/group where the account is a member."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    async def parse(
        self, channel_username: str, limit: int = 50, keywords: list[str] | None = None
    ) -> List[DiscoveredContact]:
        """Fetch members of *channel_username* and optionally filter by *keywords*.

        Keywords are matched against the user's first_name, last_name and bio.
        """
        if not _PYROGRAM_AVAILABLE:
            logger.warning("Pyrogram not available, cannot parse channel members")
            return []

        results: List[DiscoveredContact] = []
        client = self._client
        temporary_client = False

        if client is None:
            settings = get_settings()
            if settings.telegram_api_id and settings.telegram_api_hash:
                client = Client(
                    name="channel_parser",
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    in_memory=True,
                )
                temporary_client = True
                await client.start()

        if client is None:
            logger.warning("No Telegram client available for channel parsing")
            return []

        keywords_lower = [k.lower() for k in (keywords or [])]

        try:
            members = client.get_chat_members(channel_username, limit=limit)
            usernames_seen: set[str] = set()

            async for member in members:
                user: User | None = getattr(member, "user", None)
                if not user:
                    continue

                username = user.username
                if not username or username.lower() in usernames_seen:
                    continue
                usernames_seen.add(username.lower())

                # Keyword filtering on profile fields
                profile_text = " ".join(
                    filter(
                        None,
                        [
                            user.first_name or "",
                            user.last_name or "",
                            getattr(user, "bio", None) or "",
                        ],
                    )
                ).lower()

                if keywords_lower and not any(k in profile_text for k in keywords_lower):
                    continue

                results.append(
                    DiscoveredContact(
                        telegram_username=username,
                        telegram_user_id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        bio=getattr(user, "bio", None),
                        source="channel_parse",
                    )
                )

                if len(results) >= limit:
                    break
        except Exception as exc:
            logger.warning("Channel members parsing failed for %s: %s", channel_username, exc)
        finally:
            if temporary_client:
                try:
                    await client.stop()
                except Exception:
                    logger.warning("Failed to stop channel parser client", exc_info=True)

        return results


async def enrich_contact(
    contact: DiscoveredContact,
    client: Any | None = None,
) -> DiscoveredContact:
    """Enrich a discovered contact via Pyrogram get_users.

    Fills missing first_name, last_name and bio from the public profile.
    """
    if not _PYROGRAM_AVAILABLE or not contact.telegram_username:
        return contact

    temp_client = False
    if client is None:
        settings = get_settings()
        if settings.telegram_api_id and settings.telegram_api_hash:
            client = Client(
                name="enricher",
                api_id=settings.telegram_api_id,
                api_hash=settings.telegram_api_hash,
                in_memory=True,
            )
            temp_client = True
            await client.start()

    if client is None:
        return contact

    try:
        users = await client.get_users(contact.telegram_username)
        user = users[0] if isinstance(users, list) else users
        if user and not getattr(user, "is_deleted", False):
            contact.telegram_user_id = user.id
            contact.first_name = contact.first_name or user.first_name
            contact.last_name = contact.last_name or user.last_name
            contact.bio = contact.bio or getattr(user, "bio", None)
    except Exception as exc:
        logger.debug("Enrichment failed for %s: %s", contact.telegram_username, exc)
    finally:
        if temp_client:
            try:
                await client.stop()
            except Exception:
                logger.warning("Failed to stop enrichment client", exc_info=True)

    return contact


async def discover_leads(
    criteria: LeadCriteria,
    source: str = "telegram_search",
    client: Any | None = None,
) -> List[DiscoveredContact]:
    """High-level discovery dispatcher.

    Args:
        criteria: Search criteria.
        source: One of ``telegram_search``, ``channel_parse``, ``external_api``.
        client: Optional Pyrogram client to reuse.

    Returns:
        List of discovered contacts.
    """
    if source == "telegram_search":
        searcher = TelegramPublicSearch(client=client)
        return await searcher.search(criteria.query, limit=criteria.limit)

    if source == "channel_parse":
        parser = ChannelMembersParser(client=client)
        return await parser.parse(
            channel_username=criteria.query,
            limit=criteria.limit,
            keywords=criteria.keywords,
        )

    if source == "external_api":
        adapter = GenericJSONAdapter()
        return await adapter.search(criteria)

    logger.warning("Unknown discovery source: %s", source)
    return []
