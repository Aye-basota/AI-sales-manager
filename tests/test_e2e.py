"""End-to-end test covering the full sales cycle."""

import uuid
from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bots.admin_bot import handle_qualify
from app.bots.inbound_listener import _handle_inbound_message
from app.core.scheduler import process_campaigns
from app.models.campaign import Campaign, CampaignContact
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.script import Script
from app.models.telegram_account import TelegramAccount
from tests.conftest import MockResult, build_mock_session


@pytest.fixture
def e2e_script():
    return Script(
        id=uuid.uuid4(),
        name="E2E Script",
        role_prompt="You are a sales assistant",
        target_audience="Startups",
        goal="Book a meeting",
        success_criteria="Meeting scheduled",
        tone="professional",
        max_messages=3,
        follow_up_delay_hours=24,
        working_hours_start=time(0, 0),
        working_hours_end=time(23, 59, 59),
        timezone="UTC",
        is_active=True,
        created_at=datetime.now(),
    )


@pytest.fixture
def e2e_contacts():
    contacts = []
    for i in range(3):
        contacts.append(
            Contact(
                id=uuid.uuid4(),
                telegram_username=f"e2euser{i}",
                telegram_user_id=1000 + i,
                first_name=f"Contact{i}",
                last_name="Test",
                status="new",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
    return contacts


@pytest.fixture
def e2e_account():
    return TelegramAccount(
        id=uuid.uuid4(),
        phone="+1234567890",
        status="ready",
        daily_messages_sent=0,
        session_string="test_session",
    )


@pytest.mark.asyncio
async def test_full_sales_cycle(client, mock_db, e2e_script, e2e_contacts, e2e_account):
    # --- 1. Create Script via API ---
    script_payload = {
        "name": e2e_script.name,
        "role_prompt": e2e_script.role_prompt,
        "goal": e2e_script.goal,
        "working_hours_start": "00:00:00",
        "working_hours_end": "23:59:59",
        "timezone": "UTC",
    }
    resp = client.post("/scripts", json=script_payload)
    assert resp.status_code == 201
    script_id = uuid.UUID(resp.json()["id"])
    e2e_script.id = script_id

    # --- 2. Create 3 contacts via API ---
    contact_ids = []
    for contact in e2e_contacts:
        payload = {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "telegram_username": contact.telegram_username,
            "telegram_user_id": contact.telegram_user_id,
            "status": "new",
        }
        resp = client.post("/contacts", json=payload)
        assert resp.status_code == 201
        contact.id = uuid.UUID(resp.json()["id"])
        contact_ids.append(str(contact.id))

    # --- 3. Create Campaign and attach contacts ---
    campaign_payload = {
        "name": "E2E Campaign",
        "script_id": str(script_id),
        "status": "draft",
    }
    resp = client.post("/campaigns", json=campaign_payload)
    assert resp.status_code == 201
    campaign_id = uuid.UUID(resp.json()["id"])

    campaign = Campaign(
        id=campaign_id,
        script_id=script_id,
        name="E2E Campaign",
        status="draft",
        total_contacts=0,
        created_at=datetime.now(),
    )
    mock_db.execute.return_value = MockResult([campaign])
    resp = client.post(
        f"/campaigns/{campaign_id}/contacts", json={"contact_ids": contact_ids}
    )
    assert resp.status_code == 201

    # Start campaign
    campaign.status = "draft"
    mock_db.execute.return_value = MockResult([campaign])
    with patch("app.api.campaigns.process_campaigns", new_callable=AsyncMock):
        resp = client.post(f"/campaigns/{campaign_id}/start")
    assert resp.status_code == 200
    assert campaign.status == "running"

    # --- 4, 5, 6: Trigger scheduler with mocked SellerClient ---
    ccs = [
        CampaignContact(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            contact_id=c.id,
            status="pending",
            message_count=0,
        )
        for c in e2e_contacts
    ]

    scheduler_results = [
        MockResult([campaign]),  # running campaigns
        MockResult([e2e_script]),  # script
        MockResult(ccs),  # campaign contacts
    ]
    for contact in e2e_contacts:
        scheduler_results.extend(
            [
                MockResult([contact]),  # contact
                MockResult([]),  # conversation not found
                MockResult([e2e_account]),  # account
                MockResult([]),  # prior same-account contact history
            ]
        )
    # Extra padding in case additional execute() calls happen
    scheduler_results.extend([MockResult([]) for _ in range(10)])

    scheduler_db = build_mock_session()
    scheduler_db.execute.side_effect = scheduler_results

    with patch("app.core.scheduler.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=scheduler_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.llm.engine.LLMEngine") as MockEngine:
            engine_inst = MockEngine.return_value
            engine_inst.generate_response_with_guardrails = AsyncMock(
                return_value={
                    "text": "Hello from E2E",
                    "model": "gpt-4",
                    "tokens_used": 10,
                }
            )

            with patch("app.bots.seller_client.SellerClient") as MockClient:
                seller_inst = MockClient.return_value
                seller_inst.start = AsyncMock()
                seller_inst.send_message = AsyncMock(return_value={"message_id": 1})
                seller_inst.stop = AsyncMock()
                seller_inst.read_history = AsyncMock()
                seller_inst.set_online = AsyncMock()
                seller_inst.set_typing = AsyncMock()
                seller_inst._client = MagicMock()

                base_dt = datetime(2024, 6, 1, 12, 0, 0)
                call_idx = 0

                def _now_side_effect(*args, **kwargs):
                    nonlocal call_idx
                    t = base_dt + timedelta(seconds=call_idx * 31)
                    call_idx += 1
                    return t

                with patch("app.core.scheduler.datetime") as mock_datetime:
                    mock_datetime.now.side_effect = _now_side_effect
                    await process_campaigns(scheduler_db)

                # Verify initial messages were sent to all 3 contacts
                assert seller_inst.send_message.call_count == len(e2e_contacts)

    # --- 7, 8, 9: Simulate inbound reply with meeting_intent ---
    target_contact = e2e_contacts[0]
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=target_contact.id,
        campaign_id=campaign_id,
        current_state="warm",
    )

    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        contact_id=target_contact.id,
        status="initial_sent",
    )

    inbound_db = build_mock_session()
    inbound_db.execute.side_effect = [
        MockResult([target_contact]),  # find contact by telegram_user_id
        MockResult([conversation]),  # find latest conversation
        MockResult([campaign]),  # find campaign
        MockResult([cc]),  # find campaign contact for analytics
        MockResult([e2e_script]),  # find script
        MockResult([e2e_account]),  # find account for inbound rate limits
    ]

    # Mock Pyrogram message
    pyro_message = MagicMock()
    pyro_message.from_user = MagicMock(id=target_contact.telegram_user_id)
    pyro_message.text = "Yes, tomorrow at 11:00 works for me"

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=inbound_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="meeting_intent",
        ):
            with patch("app.llm.engine.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={
                        "text": "Great, let's schedule!",
                        "model": "gpt-4",
                        "tokens_used": 5,
                    }
                )

                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.get_conversation_context",
                        new_callable=AsyncMock,
                        return_value={"messages": [], "facts": {}},
                    ):
                        with patch(
                            "app.bots.inbound_listener.add_message",
                            new_callable=AsyncMock,
                        ) as mock_add_msg:
                            with patch(
                                "app.bots.inbound_listener.NotificationService.send_hot_lead_alert",
                                new_callable=AsyncMock,
                            ) as mock_notif:
                                await _handle_inbound_message(
                                    e2e_account, seller_inst, pyro_message
                                )

                                # Verify both inbound and outbound messages were saved
                                assert mock_add_msg.call_count == 2
                                assert e2e_account.daily_messages_sent >= 1

                                # 10. Verify notification was sent to Admin Bot
                                mock_notif.assert_awaited_once()

    # Verify conversation state transitioned to meeting_booked
    assert conversation.current_state == "meeting_booked"

    # --- 11. Verify operator_status changed to qualified via admin bot ---
    mock_callback = AsyncMock()
    mock_callback.data = f"qualify:{conversation.id}"

    admin_db = build_mock_session()
    admin_db.execute.return_value = MockResult([conversation])

    with patch("app.bots.admin_bot.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=admin_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        await handle_qualify(mock_callback)

        assert conversation.operator_status == "qualified"
        mock_callback.answer.assert_awaited_once_with("✅ Отмечено: готов к работе")
