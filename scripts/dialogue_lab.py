"""Autonomous dialogue-quality lab for AI Sales Manager.

The lab uses the real database, prompts, LLM engine, intent classifier, and
inbound handler, but replaces Telegram transport and admin notifications with
local recorders. It lets us test lead-reply scenarios without asking a human to
answer in Telegram.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import delete  # noqa: E402

import app.bots.inbound_listener as inbound_listener  # noqa: E402
from app.bots.inbound_listener import _handle_inbound_message  # noqa: E402
from app.core.funnel import DEFAULT_FUNNEL_STAGES  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.llm.guardrails import evaluate_guardrails  # noqa: E402
from app.models.campaign import Campaign, CampaignContact  # noqa: E402
from app.models.contact import Contact  # noqa: E402
from app.models.conversation import Conversation, Message  # noqa: E402
from app.models.script import Script  # noqa: E402
from app.models.telegram_account import TelegramAccount  # noqa: E402


DEFAULT_SCENARIOS = [
    {
        "name": "hesitation",
        "lead": "Не уверен, у нас сейчас и так все вручную работает. Может потом.",
        "expected": {"positive", "objection", "informational"},
    },
    {
        "name": "pricing_question",
        "lead": "Сколько это стоит? И чем вы лучше обычного менеджера по продажам?",
        "expected": {"question", "informational"},
    },
    {
        "name": "spam_objection",
        "lead": "Выглядит как спам. Не хочу, чтобы наш аккаунт заблокировали.",
        "expected": {"objection", "negative"},
    },
    {
        "name": "hard_refusal",
        "lead": "Не пишите мне больше, нам это не нужно.",
        "expected": {"negative"},
    },
    {
        "name": "meeting_intent",
        "lead": "Ок, звучит интересно. Давай созвон завтра после обеда.",
        "expected": {"meeting_intent", "positive"},
    },
    {
        "name": "technical_risk",
        "lead": "Как вы получаете контакты и что будет, если Telegram начнет ругаться?",
        "expected": {"question", "objection", "informational"},
    },
    {
        "name": "bot_check",
        "lead": "Ты бот? Ответь честно, это автоматическая рассылка?",
        "expected": {"question", "objection", "informational"},
    },
    {
        "name": "impatient_short",
        "lead": "???",
        "expected": {"informational", "question", "objection"},
    },
    {
        "name": "soft_not_now",
        "lead": "Сейчас не до этого, напишите через пару месяцев.",
        "expected": {"objection", "informational"},
    },
    {
        "name": "unsubscribe_data",
        "lead": "Удалите мои данные и больше не пишите.",
        "expected": {"negative"},
    },
    {
        "name": "wrong_person",
        "lead": "Это вообще не ко мне, я не занимаюсь продажами.",
        "expected": {"objection", "informational"},
    },
    {
        "name": "not_decision_maker",
        "lead": "Я не принимаю такие решения, этим руководитель отдела занимается.",
        "expected": {"informational", "objection"},
    },
    {
        "name": "send_materials",
        "lead": "Пришлите коротко, что у вас есть, я посмотрю позже.",
        "expected": {"positive", "question", "informational"},
    },
    {
        "name": "already_have_tool",
        "lead": "У нас уже есть CRM и менеджеры, зачем еще один инструмент?",
        "expected": {"objection", "question"},
    },
    {
        "name": "budget_objection",
        "lead": "Если это дорого, нам точно не подойдет.",
        "expected": {"objection"},
    },
    {
        "name": "integration_question",
        "lead": "А с amoCRM или Bitrix24 это можно связать?",
        "expected": {"question"},
    },
    {
        "name": "security_question",
        "lead": "Что с безопасностью данных и доступами к Telegram аккаунту?",
        "expected": {"question", "objection"},
    },
    {
        "name": "case_study_question",
        "lead": "Есть кейсы по B2B SaaS или это пока только теория?",
        "expected": {"question"},
    },
    {
        "name": "angry_refusal",
        "lead": "Да отстаньте уже, не интересно.",
        "expected": {"negative"},
    },
    {
        "name": "short_positive",
        "lead": "Ок, интересно",
        "expected": {"positive", "informational"},
    },
    {
        "name": "short_yes",
        "lead": "Да",
        "expected": {"positive", "informational"},
    },
    {
        "name": "asks_who_are_you",
        "lead": "А вы кто и откуда у вас мой контакт?",
        "expected": {"question", "objection"},
    },
    {
        "name": "competitor_compare",
        "lead": "Чем вы отличаетесь от обычной рассылки через Telegram?",
        "expected": {"question"},
    },
    {
        "name": "exact_meeting_time",
        "lead": "Можем завтра в 16:00, если это займет не больше 20 минут.",
        "expected": {"meeting_intent"},
    },
    {
        "name": "call_now",
        "lead": "Можете сейчас набрать?",
        "expected": {"meeting_intent", "question"},
    },
    {
        "name": "one_word_no",
        "lead": "Нет",
        "expected": {"negative", "objection"},
    },
    {
        "name": "too_many_questions_from_lead",
        "lead": "Сколько стоит, как подключается, кто пишет тексты и какие лимиты в Telegram?",
        "expected": {"question"},
    },
    {
        "name": "asks_for_email",
        "lead": "Напишите лучше на почту, тут неудобно.",
        "expected": {"positive", "informational", "question"},
    },
    {
        "name": "english_reply",
        "lead": "Can you explain in English what this does?",
        "expected": {"question", "informational"},
    },
    {
        "name": "manual_process_details",
        "lead": "У нас лиды из конференций, потом менеджер руками пишет в Telegram.",
        "expected": {"informational", "positive"},
    },
    {
        "name": "fear_spam_reports",
        "lead": "Боюсь жалоб на спам, у нас уже был неприятный опыт.",
        "expected": {"objection"},
    },
    {
        "name": "asks_for_price_only",
        "lead": "Цена?",
        "expected": {"question"},
    },
    {
        "name": "wants_human",
        "lead": "Можно с живым человеком поговорить, а не вот это всё?",
        "expected": {"meeting_intent", "objection", "question"},
    },
    {
        "name": "confused_context",
        "lead": "Не понял, о чем речь вообще.",
        "expected": {"question", "informational", "objection"},
    },
    {
        "name": "legal_compliance",
        "lead": "Это вообще легально с точки зрения персональных данных?",
        "expected": {"question", "objection"},
    },
    {
        "name": "asks_to_pause",
        "lead": "Давайте вернемся к этому в конце квартала.",
        "expected": {"objection", "informational", "positive"},
    },
]

DEFAULT_LIMIT = 30

HARD_STOP_SCENARIOS = {
    "hard_refusal",
    "unsubscribe_data",
    "angry_refusal",
    "one_word_no",
}
MEETING_SCENARIOS = {
    "meeting_intent",
    "exact_meeting_time",
}
RISK_SCENARIOS = {
    "spam_objection",
    "technical_risk",
    "security_question",
    "fear_spam_reports",
    "legal_compliance",
}


@dataclass
class FakeUser:
    id: int
    username: str = "dialogue_lab_lead"
    first_name: str = "Test"
    last_name: str = "Lead"


@dataclass
class FakeMessage:
    from_user: FakeUser
    text: str


@dataclass
class CapturedSend:
    user_id: int
    text: str
    typing_delay_ms: int


@dataclass
class CapturingClient:
    sends: list[CapturedSend] = field(default_factory=list)
    read_history_calls: int = 0
    set_online_calls: int = 0

    async def read_history(self, user_id: int) -> None:
        self.read_history_calls += 1

    async def set_online(self) -> None:
        self.set_online_calls += 1

    async def send_message(
        self, user_id: int, text: str, typing_delay_ms: int = 0
    ) -> dict[str, Any]:
        self.sends.append(CapturedSend(user_id, text, typing_delay_ms))
        return {"message_id": len(self.sends), "text": text}


@dataclass
class CapturingNotifications:
    hot_leads: list[dict[str, Any]] = field(default_factory=list)

    async def send_hot_lead_alert(
        self,
        contact: Contact,
        conversation: Conversation,
        last_message_text: str = "",
    ) -> None:
        self.hot_leads.append(
            {
                "contact_id": str(contact.id),
                "conversation_id": str(conversation.id),
                "state": conversation.current_state,
                "last_message_text": last_message_text,
            }
        )


@dataclass
class ScenarioResult:
    name: str
    lead_text: str
    response_text: str
    chunks: list[CapturedSend]
    intent: str | None
    state: str | None
    stage: str | None
    notifications: int
    issues: list[str]


async def _fast_sleep(_: float) -> None:
    return None


def _build_script(run_id: str) -> Script:
    return Script(
        name=f"Dialogue Lab {run_id}",
        role_prompt=(
            "Ты живой B2B sales manager. Пиши по-русски, коротко и спокойно. "
            "Не называй себя ботом или ИИ. Не дави. Если человек сомневается, "
            "сначала уточни причину и сними риск."
        ),
        target_audience="B2B founders and sales managers",
        goal="показать ценность AI Sales Manager и договориться о коротком созвоне",
        success_criteria="лид согласился на короткий созвон или попросил детали",
        tone="friendly",
        max_messages=4,
        follow_up_delay_hours=24,
        working_hours_start=time(0, 0),
        working_hours_end=time(23, 59),
        timezone="UTC",
        sales_funnel=list(DEFAULT_FUNNEL_STAGES),
        first_message_goal="trust",
        call_to_action="15-минутный созвон",
        language="ru",
        emoji_policy="forbidden",
        max_first_message_length=200,
        is_active=True,
    )


async def _create_context(run_id: str, lead_id: int, scenario_name: str):
    script = _build_script(run_id)
    contact = Contact(
        telegram_user_id=lead_id,
        telegram_username=f"dialogue_lab_{scenario_name}"[:32],
        first_name="Test",
        last_name="Lead",
        company_name="Demo Company",
        position="Head of Sales",
        source="dialogue_lab",
        last_source="dialogue_lab",
        is_valid="valid",
    )
    campaign = Campaign(
        name=f"Dialogue Lab {scenario_name}",
        status="running",
        total_contacts=1,
        processed_contacts=1,
        replied_count=0,
        started_at=datetime.now(timezone.utc),
    )
    conversation = Conversation(
        contact_id=contact.id,
        campaign_id=campaign.id,
        current_state="warm",
        conversation_stage="engagement",
        facts_extracted={},
    )
    account = TelegramAccount(
        id=uuid4(),
        phone="+10000000000",
        username="dialogue_lab_seller",
        status="ready",
        daily_messages_sent=0,
        last_message_at=datetime.now(timezone.utc),
        session_string="synthetic",
    )

    async with AsyncSessionLocal() as session:
        session.add(script)
        await session.flush()

        campaign.script_id = script.id
        session.add(campaign)
        session.add(contact)
        await session.flush()

        conversation.contact_id = contact.id
        conversation.campaign_id = campaign.id
        session.add(conversation)
        await session.flush()
        session.add(
            Message(
                conversation_id=conversation.id,
                direction="outbound",
                content=(
                    "Привет. Пишу коротко: помогаем командам аккуратно начинать "
                    "диалоги с потенциальными клиентами без лишней ручной рутины."
                ),
                message_type="text",
                llm_model="dialogue_lab_seed",
                tokens_used=0,
            )
        )
        session.add(
            CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="initial_sent",
                initial_sent_at=datetime.now(timezone.utc),
                last_message_at=datetime.now(timezone.utc),
                message_count=1,
            )
        )
        await session.commit()
        await session.refresh(contact)
        await session.refresh(conversation)

    return script.id, campaign.id, contact.id, conversation.id, account


async def _cleanup(ids: list[dict[str, Any]]) -> None:
    async with AsyncSessionLocal() as session:
        for item in ids:
            await session.execute(
                delete(Message).where(Message.conversation_id == item["conversation_id"])
            )
            await session.execute(
                delete(Conversation).where(Conversation.id == item["conversation_id"])
            )
            await session.execute(
                delete(CampaignContact).where(
                    CampaignContact.campaign_id == item["campaign_id"]
                )
            )
            await session.execute(delete(Campaign).where(Campaign.id == item["campaign_id"]))
            await session.execute(delete(Contact).where(Contact.id == item["contact_id"]))
            await session.execute(delete(Script).where(Script.id == item["script_id"]))
        await session.commit()


async def _load_conversation(conversation_id):
    async with AsyncSessionLocal() as session:
        conversation = await session.get(Conversation, conversation_id)
        return conversation


def _analyze_result(
    scenario: dict[str, Any],
    response_text: str,
    chunks: list[CapturedSend],
    intent: str | None,
    state: str | None,
) -> list[str]:
    issues: list[str] = []
    expected = scenario["expected"]

    if intent not in expected:
        issues.append(f"intent={intent!r} outside expected {sorted(expected)}")

    guardrails = evaluate_guardrails(response_text, [])
    if not guardrails.approved:
        issues.append(f"guardrails violations: {', '.join(guardrails.violations)}")

    if not response_text.strip():
        issues.append("empty response")
    if len(response_text) > 650:
        issues.append(f"response too long: {len(response_text)} chars")
    if response_text.count("?") > 1:
        issues.append("too many questions in one response")
    if response_text.count("\n\n") > 1:
        issues.append("too many paragraph breaks")
    if len(chunks) > 3:
        issues.append(f"too many Telegram chunks: {len(chunks)}")
    if any(len(chunk.text) > 450 for chunk in chunks):
        issues.append("a Telegram chunk is too long")
    if any(chunk.typing_delay_ms <= 0 for chunk in chunks):
        issues.append("missing typing delay for at least one chunk")

    lower = response_text.lower()
    if lower.startswith(("понимаю, ", "спасибо за ответ")):
        issues.append("robotic opening")
    if scenario["name"] not in MEETING_SCENARIOS and state not in {
        "meeting_booked",
        "closed",
    }:
        if any(marker in lower for marker in ("15-минут", "созвон", "встречу")):
            issues.append("premature meeting CTA")
    if scenario["name"] == "bot_check" and any(
        phrase in lower for phrase in ("я бот", "я ии", "искусственный интеллект")
    ):
        issues.append("bot_check response reveals automation")
    if scenario["name"] in RISK_SCENARIOS and intent != "negative" and not any(
        marker in lower
        for marker in ("заблок", "блокиров", "риск", "лимит", "данн", "доступ")
    ):
        issues.append("risk concern was not addressed")
    if scenario["name"] in MEETING_SCENARIOS and state not in {"hot", "meeting_booked"}:
        issues.append(f"meeting intent did not become hot/meeting_booked: {state}")
    if state == "meeting_booked" and "?" in response_text:
        issues.append("meeting response asked a follow-up question")
    if scenario["name"] in HARD_STOP_SCENARIOS:
        if state != "closed":
            issues.append(f"hard refusal did not close conversation: {state}")
        if "?" in response_text:
            issues.append("hard refusal response asked a follow-up question")
    if "price" in scenario["name"] or "pricing" in scenario["name"]:
        if any(marker in response_text for marker in ("₽", "$", " руб", " долларов")):
            issues.append("pricing response invented an exact price")

    return issues


async def run_lab(args: argparse.Namespace) -> list[ScenarioResult]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    created_ids: list[dict[str, Any]] = []
    results: list[ScenarioResult] = []
    original_notification_service = inbound_listener.NotificationService

    async def scenario_run(scenario: dict[str, Any], idx: int) -> ScenarioResult:
        lead_id = args.lead_id + idx + 1
        script_id, campaign_id, contact_id, conversation_id, account = await _create_context(
            run_id, lead_id, scenario["name"]
        )
        created_ids.append(
            {
                "script_id": script_id,
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "conversation_id": conversation_id,
            }
        )

        client = CapturingClient()
        notifications = CapturingNotifications()
        inbound_listener.NotificationService = lambda: notifications

        message = FakeMessage(
            from_user=FakeUser(
                id=lead_id,
                username=f"dialogue_lab_{scenario['name']}"[:32],
            ),
            text=scenario["lead"],
        )

        await _handle_inbound_message(account, client, message)
        conversation = await _load_conversation(conversation_id)
        response_text = "\n".join(chunk.text for chunk in client.sends)
        intent = None
        if conversation and conversation.facts_extracted:
            intent = conversation.facts_extracted.get("last_intent")

        issues = _analyze_result(
            scenario=scenario,
            response_text=response_text,
            chunks=client.sends,
            intent=intent,
            state=conversation.current_state if conversation else None,
        )
        return ScenarioResult(
            name=scenario["name"],
            lead_text=scenario["lead"],
            response_text=response_text,
            chunks=client.sends,
            intent=intent,
            state=conversation.current_state if conversation else None,
            stage=conversation.conversation_stage if conversation else None,
            notifications=len(notifications.hot_leads),
            issues=issues,
        )

    try:
        from unittest.mock import patch

        with patch("app.bots.inbound_listener.asyncio.sleep", new=_fast_sleep):
            for idx, scenario in enumerate(DEFAULT_SCENARIOS[: args.limit]):
                results.append(await scenario_run(scenario, idx))
    finally:
        inbound_listener.NotificationService = original_notification_service
        if not args.keep_db:
            await _cleanup(created_ids)

    return results


def write_report(results: list[ScenarioResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dialogue Lab Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
    ]
    failed = [result for result in results if result.issues]
    lines.append(f"- Scenarios: {len(results)}")
    lines.append(f"- Scenarios with issues: {len(failed)}")
    lines.append("")

    for result in results:
        status = "FAIL" if result.issues else "PASS"
        lines.extend(
            [
                f"## {status}: {result.name}",
                "",
                f"Lead: {result.lead_text}",
                "",
                f"Intent: `{result.intent}`",
                f"State: `{result.state}`",
                f"Stage: `{result.stage}`",
                f"Notifications: `{result.notifications}`",
                "",
                "Bot response:",
                "",
                "```text",
                result.response_text or "(empty)",
                "```",
                "",
                "Telegram chunks:",
                "",
            ]
        )
        for idx, chunk in enumerate(result.chunks, 1):
            lines.append(
                f"{idx}. {len(chunk.text)} chars, typing_delay_ms={chunk.typing_delay_ms}"
            )
        if result.issues:
            lines.extend(["", "Issues:", ""])
            for issue in result.issues:
                lines.append(f"- {issue}")
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run autonomous dialogue scenarios.")
    parser.add_argument("--lead-id", type=int, required=True)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--keep-db", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / ".dialogue-lab" / "latest.md",
    )
    return parser.parse_args()


async def main() -> None:
    engine.echo = False
    for logger_name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
        logging.getLogger(logger_name).disabled = True

    args = parse_args()
    results = await run_lab(args)
    write_report(results, args.output)
    failed = [result for result in results if result.issues]

    print(f"Dialogue lab finished: {len(results)} scenarios, {len(failed)} with issues")
    print(f"Report: {args.output}")
    for result in results:
        status = "FAIL" if result.issues else "PASS"
        print(
            f"{status} {result.name}: intent={result.intent}, "
            f"state={result.state}, chunks={len(result.chunks)}"
        )
        for issue in result.issues:
            print(f"  - {issue}")


if __name__ == "__main__":
    asyncio.run(main())
