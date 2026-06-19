import uuid
from datetime import datetime, time
from typing import Any, List
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db


class MockScalarResult:
    def __init__(self, items: List[Any]):
        self._items = items

    def all(self):
        return self._items

    def one(self):
        return self._items[0]

    def first(self):
        return self._items[0] if self._items else None


class MockResult:
    def __init__(self, items: List[Any] = None, scalar_value: Any = None):
        self._items = items or []
        self._scalar_value = scalar_value

    def scalars(self):
        return MockScalarResult(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalar(self):
        return self._scalar_value

    def one(self):
        return self._items[0] if self._items else None

    def all(self):
        return self._items


def build_mock_session(results: List[Any] = None, scalar_value: Any = None):
    from unittest.mock import MagicMock
    session = AsyncMock()
    result = MockResult(results, scalar_value)
    session.execute.return_value = result
    session.add = MagicMock()

    async def refresh_side_effect(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, 'created_at') and obj.created_at is None:
            obj.created_at = datetime.now()
        if hasattr(obj, 'updated_at') and obj.updated_at is None:
            obj.updated_at = datetime.now()
        if hasattr(obj, 'source') and obj.source is None:
            obj.source = 'csv_import'

    session.refresh.side_effect = refresh_side_effect
    return session


@pytest.fixture
def mock_db():
    return build_mock_session()


@pytest.fixture
def client(mock_db):
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]


@pytest.fixture
def sample_script():
    from app.models.script import Script
    script = Script(
        id=uuid.uuid4(),
        name="Test Script",
        role_prompt="You are a sales assistant",
        target_audience="Startups",
        goal="Book a meeting",
        success_criteria="Meeting scheduled",
        tone="professional",
        first_message_goal="hook",
        call_to_action="15-минутный созвон",
        language="ru",
        emoji_policy="forbidden",
        max_first_message_length=200,
        max_messages=3,
        follow_up_delay_hours=24,
        working_hours_start=time(9, 0),
        working_hours_end=time(18, 0),
        timezone="Europe/Moscow",
        is_active=True,
        created_at=datetime.now(),
    )
    return script


@pytest.fixture
def sample_contact():
    from app.models.contact import Contact
    contact = Contact(
        id=uuid.uuid4(),
        telegram_username="testuser",
        phone="+1234567890",
        first_name="John",
        last_name="Doe",
        company_name="Acme",
        position="CEO",
        city="New York",
        industry="Tech",
        source="csv_import",
        icp_score=85,
        status="new",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return contact


@pytest.fixture
def sample_campaign():
    from app.models.campaign import Campaign
    campaign = Campaign(
        id=uuid.uuid4(),
        script_id=uuid.uuid4(),
        name="Test Campaign",
        status="draft",
        total_contacts=100,
        processed_contacts=50,
        replied_count=20,
        qualified_count=10,
        meeting_booked_count=5,
        created_at=datetime.now(),
    )
    return campaign


@pytest.fixture
def sample_conversation():
    from app.models.conversation import Conversation
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        current_state="cold",
        conversation_stage="hook",
        sentiment="positive",
        facts_extracted={},
        operator_status="open",
        operator_notes="",
        created_at=datetime.now(),
    )
    return conversation


@pytest.fixture
def sample_message():
    from app.models.conversation import Message
    message = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        direction="outbound",
        content="Hello",
        message_type="text",
        intent_classification="greeting",
        llm_model="gpt-4",
        tokens_used=15,
        typing_delay_ms=500,
        sent_at=datetime.now(),
    )
    return message
