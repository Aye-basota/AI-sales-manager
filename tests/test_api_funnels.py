"""Tests for funnel upload/preview API (TECH-04/TECH-05)."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from tests.conftest import MockResult
from app.models.funnel import Funnel
from app.services.funnel_parser import (
    FunnelParseError,
    parse_funnel,
    parse_funnel_json,
    parse_funnel_text,
)


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


def test_parse_funnel_json_accepts_name_alias_and_defaults():
    stages = parse_funnel_json(
        json.dumps({"stages": [{"name": "trust"}, {"stage": "cta", "max_length": 100}]})
    )

    assert stages == [
        {
            "stage": "trust",
            "goal": "",
            "instructions": "",
            "max_length": 400,
            "allow_call_to_action": False,
        },
        {
            "stage": "cta",
            "goal": "",
            "instructions": "",
            "max_length": 100,
            "allow_call_to_action": False,
        },
    ]


def test_parse_funnel_rejects_invalid_structures():
    invalid_cases = [
        ('{"stages": "bad"}', "Funnel stages must be a list"),
        ("[]", "JSON root must be an object"),
        ('{"steps": []}', "Missing 'stages'"),
        ('{"stages": []}', "at least one stage"),
        ('{"stages": ["bad"]}', "Stage 1 must be an object"),
        ('{"stages": [{}]}', "missing a 'stage'"),
        ('{"stages": [{"stage": "trust"}, {"stage": "trust"}]}', "Duplicate"),
    ]

    for content, message in invalid_cases:
        with pytest.raises(FunnelParseError, match=message):
            parse_funnel_json(content)


def test_parse_funnel_text_strips_stage_prefix_and_requires_headings():
    stages = parse_funnel_text(
        """Intro ignored
## Stage 1: trust
Build trust.
## Stage 2 - cta
Offer demo.
"""
    )

    assert [stage["stage"] for stage in stages] == ["trust", "cta"]
    assert stages[0]["instructions"] == "Build trust."
    assert stages[1]["instructions"] == "Offer demo."

    with pytest.raises(FunnelParseError, match="at least one stage"):
        parse_funnel_text("plain text without headings")


def test_parse_funnel_dispatches_by_format_and_rejects_unknown_format():
    assert parse_funnel(VALID_FUNNEL_JSON, " JSON ")[0]["stage"] == "trust"
    assert parse_funnel(VALID_FUNNEL_TEXT, "text")[0]["stage"] == "trust"

    with pytest.raises(FunnelParseError, match="Unsupported format"):
        parse_funnel(VALID_FUNNEL_JSON, "yaml")


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


def test_upload_funnel_invalid_content_returns_422(client):
    payload = {
        "content": "not json",
        "format": "json",
        "name": "Bad Upload",
    }

    response = client.post("/api/funnels/upload", json=payload)

    assert response.status_code == 422


def test_upload_funnel_deletes_existing_when_allowed(client, mock_db, sample_campaign):
    sample_campaign.status = "draft"
    existing_funnel = Funnel(
        id=uuid4(),
        name="Old",
        campaign_id=sample_campaign.id,
        stages=[],
        source_format="json",
    )
    mock_db.execute.side_effect = [
        MockResult([sample_campaign]),
        MockResult([existing_funnel]),
    ]
    payload = {
        "content": VALID_FUNNEL_JSON,
        "format": "json",
        "name": "Replacement",
        "campaign_id": str(sample_campaign.id),
    }

    response = client.post("/api/funnels/upload", json=payload)

    assert response.status_code == 201
    mock_db.delete.assert_awaited_once_with(existing_funnel)


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


def test_list_funnels(client, mock_db):
    funnel = Funnel(
        id=uuid4(),
        name="Persisted Funnel",
        campaign_id=None,
        stages=[{"stage": "trust", "goal": "Build trust"}],
        source_format="json",
        notes="Imported",
        created_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )
    mock_db.execute.return_value = MockResult([funnel])

    response = client.get("/api/funnels")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(funnel.id)
    assert data[0]["name"] == "Persisted Funnel"
    assert data[0]["stages"][0]["stage"] == "trust"


def test_get_funnel(client, mock_db):
    funnel = Funnel(
        id=uuid4(),
        name="Persisted Funnel",
        campaign_id=None,
        stages=[{"stage": "cta", "allow_call_to_action": True}],
        source_format="json",
        created_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )
    mock_db.execute.return_value = MockResult([funnel])

    response = client.get(f"/api/funnels/{funnel.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(funnel.id)
    assert data["stages"][0]["allow_call_to_action"] is True


def test_get_funnel_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])

    response = client.get(f"/api/funnels/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Funnel not found"
