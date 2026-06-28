"""Seed the database with demo data for presentations and customer reviews.

Usage:
    docker-compose exec api python scripts/seed_demo_data.py
"""

import asyncio
import random
from datetime import datetime, time, timezone, timedelta

from app.db.session import AsyncSessionLocal
from app.models.script import Script
from app.models.contact import Contact
from app.models.campaign import Campaign, CampaignContact
from app.models.conversation import Conversation, Message


DEMO_COMPANIES = [
    ("Acme Corp", "Tech", "New York", "CEO"),
    ("Beta Solutions", "SaaS", "Berlin", "CTO"),
    ("Gamma Logistics", "Logistics", "Dubai", "COO"),
    ("Delta Finance", "Finance", "Singapore", "Head of Sales"),
    ("Epsilon Retail", "Retail", "London", "Marketing Director"),
]


def _make_demo_script() -> Script:
    return Script(
        name="Demo B2B Outreach Script",
        role_prompt=(
            "You are a senior sales manager at Neural Lead. "
            "You help small and medium B2B companies automate outbound sales via Telegram."
        ),
        target_audience="B2B founders and sales leaders",
        goal="Book a 15-minute discovery call",
        success_criteria="Lead agrees to a call or asks for more details",
        tone="professional",
        max_messages=2,
        follow_up_delay_hours=24,
        working_hours_start=time(9, 0),
        working_hours_end=time(18, 0),
        timezone="Europe/Moscow",
        is_active=True,
        sales_funnel=[
            {"stage": "hook", "max_length": 200},
            {"stage": "qualification", "max_length": 250},
            {"stage": "value", "max_length": 300},
            {"stage": "cta", "max_length": 200},
        ],
        first_message_goal="hook",
        call_to_action="15-минутный созвон на этой неделе",
        language="ru",
        emoji_policy="forbidden",
        max_first_message_length=200,
    )


def _make_demo_contacts() -> list[Contact]:
    contacts = []
    for idx, (company, industry, city, position) in enumerate(DEMO_COMPANIES, start=1):
        contacts.append(
            Contact(
                telegram_username=f"demouser{idx}",
                telegram_user_id=1000000000 + idx,
                phone=f"+7900000000{idx}",
                first_name=f"Demo{idx}",
                last_name="Lead",
                company_name=company,
                position=position,
                city=city,
                industry=industry,
                source="demo_seed",
                last_source="demo_seed",
                is_valid="yes",
                icp_score=random.randint(60, 95),
                status="new",
            )
        )
    return contacts


def _make_demo_campaign(script: Script, contacts: list[Contact]) -> Campaign:
    return Campaign(
        script_id=script.id,
        name="Demo Campaign",
        status="running",
        total_contacts=len(contacts),
        processed_contacts=3,
        replied_count=2,
        qualified_count=1,
        meeting_booked_count=1,
        started_at=datetime.now(timezone.utc) - timedelta(days=2),
    )


async def _seed() -> None:
    async with AsyncSessionLocal() as db:
        # Create demo script
        script = _make_demo_script()
        db.add(script)
        await db.flush()

        # Create demo contacts
        contacts = _make_demo_contacts()
        for contact in contacts:
            contact.assigned_script_id = script.id
            db.add(contact)
        await db.flush()

        # Create demo campaign
        campaign = _make_demo_campaign(script, contacts)
        db.add(campaign)
        await db.flush()

        # Link contacts to campaign
        campaign_contacts = []
        for idx, contact in enumerate(contacts):
            status = "pending"
            initial_sent_at = None
            follow_up_sent_at = None
            message_count = 0
            if idx < 3:
                status = "initial_sent"
                initial_sent_at = datetime.now(timezone.utc) - timedelta(days=1, hours=idx)
                message_count = 1
            if idx < 2:
                status = "replied"
                message_count = 2
            cc = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status=status,
                initial_sent_at=initial_sent_at,
                follow_up_sent_at=follow_up_sent_at,
                message_count=message_count,
            )
            campaign_contacts.append(cc)
            db.add(cc)
        await db.flush()

        # Create conversations and messages for replied contacts
        hot_conversation = None
        for idx, contact in enumerate(contacts[:2]):
            conversation = Conversation(
                contact_id=contact.id,
                campaign_id=campaign.id,
                current_state="hot" if idx == 0 else "follow_up",
                conversation_stage="value",
                sentiment="positive" if idx == 0 else "neutral",
                facts_extracted={"interest": "high" if idx == 0 else "medium"},
                last_message_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
            db.add(conversation)
            await db.flush()

            # Outbound initial message
            outbound = Message(
                conversation_id=conversation.id,
                direction="outbound",
                content=f"Привет, {contact.first_name}! Расскажу, как Neural Lead помогает B2B-компаниям находить клиентов в Telegram.",
                message_type="text",
                intent_classification="greeting",
                llm_model="qwen",
                tokens_used=45,
                typing_delay_ms=1200,
                sent_at=datetime.now(timezone.utc) - timedelta(hours=5),
            )
            db.add(outbound)

            # Inbound reply
            inbound = Message(
                conversation_id=conversation.id,
                direction="inbound",
                content="Интересно, давайте созвонимся во вторник" if idx == 0 else "Пришлите подробности",
                message_type="text",
                intent_classification="meeting_intent" if idx == 0 else "informational",
                sent_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
            db.add(inbound)

            if idx == 0:
                hot_conversation = conversation

        await db.commit()
        print(f"Seeded demo data: script={script.id}, campaign={campaign.id}, contacts={len(contacts)}")
        if hot_conversation:
            print(f"Hot lead conversation: {hot_conversation.id}")


if __name__ == "__main__":
    asyncio.run(_seed())
