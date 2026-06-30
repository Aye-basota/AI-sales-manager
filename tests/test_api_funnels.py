"""Tests for funnel upload/preview API (TECH-04/TECH-05)."""

import json
from uuid import uuid4

from tests.conftest import MockResult


VALID_FUNNEL_JSON = json.dumps(
    {
        "stages": [
            {"stage": "trust", "goal": "Build trust", "max_length": 200},
            {"stage": "engagement", "goal": "Engage", "max_length": 300},
            {"stage": "cta", "goal": "Close", "max_length": 400, "allow_call_to_action": True},
        ]
    }
)

VALID_FUNNEL_TEXT = """## Stage 1: trust
Build trust, no CTA.
## Stage 2: cta
Close with a meeting offer.
"""


def test_preview_funnel_json(client):
    payload = {"content": VALID_FUNNEL_JSON, "format": "json", "name": "Preview"}
    response = client.post("/api/funnels/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Preview"
    assert [s["stage"] for s in data["stages"]] == ["trust", "engagement", "cta"]
    assert data["stages"][2]["allow_call_to_action"] is True


def test_preview_funnel_text(client):
    payload = {"content": VALID_FUNNEL_TEXT, "format": "text", "name": "Text Preview"}
    response = client.post("/api/funnels/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert [s["stage"] for s in data["stages"]] == ["trust", "cta"]


def test_preview_funnel_invalid_json_returns_422(client):
    payload = {"content": "not json", "format": "json", "name": "Bad"}
    response = client.post("/api/funnels/preview", json=payload)
    assert response.status_code == 422


def test_upload_funnel_persists(client, mock_db, sample_campaign):
    mock_db.execute.side_effect = [
        MockResult([sample_campaign]),  # campaign lookup
        MockResult([]),  # no existing funnel
    ]
    payload = {
        "content": VALID_FUNNEL_JSON,
        "format": "json",
        "name": "Uploaded Funnel",
        "campaign_id": str(sample_campaign.id),
    }
    response = client.post("/api/funnels/upload", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Uploaded Funnel"
    mock_db.commit.assert_awaited_once()


def test_upload_funnel_running_campaign_without_force_returns_409(
    client, mock_db, sample_campaign
):
    sample_campaign.status = "running"
    from app.models.funnel import Funnel

    existing_funnel = Funnel(
        id=uuid4(),
        name="Old",
        campaign_id=sample_campaign.id,
        stages=[],
        source_format="json",
    )
    mock_db.execute.side_effect = [
        MockResult([sample_campaign]),  # campaign lookup
        MockResult([existing_funnel]),  # existing funnel
    ]
    payload = {
        "content": VALID_FUNNEL_JSON,
        "format": "json",
        "name": "New Funnel",
        "campaign_id": str(sample_campaign.id),
        "force": False,
    }
    response = client.post("/api/funnels/upload", json=payload)
    assert response.status_code == 409


def test_upload_funnel_missing_campaign_returns_404(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    payload = {
        "content": VALID_FUNNEL_JSON,
        "format": "json",
        "name": "Orphan Funnel",
        "campaign_id": str(uuid4()),
    }
    response = client.post("/api/funnels/upload", json=payload)
    assert response.status_code == 404
