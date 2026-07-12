import io
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from tests.conftest import MockResult
from app.api.contacts import import_contacts
from app.services.lead_discovery import DiscoveredContact


def test_list_contacts(client, mock_db, sample_contact):
    mock_db.execute.return_value = MockResult([sample_contact])
    response = client.get("/contacts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["first_name"] == "John"


def test_get_contact(client, mock_db, sample_contact):
    mock_db.execute.return_value = MockResult([sample_contact])
    response = client.get(f"/contacts/{sample_contact.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"


def test_get_contact_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.get(f"/contacts/{uuid4()}")
    assert response.status_code == 404


def test_create_contact(client, mock_db):
    payload = {
        "first_name": "Jane",
        "last_name": "Smith",
        "status": "new",
    }
    response = client.post("/contacts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Jane"
    mock_db.commit.assert_awaited_once()


def test_update_contact(client, mock_db, sample_contact):
    mock_db.execute.return_value = MockResult([sample_contact])
    payload = {"first_name": "Jane"}
    response = client.put(f"/contacts/{sample_contact.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Jane"
    mock_db.commit.assert_awaited_once()


def test_update_contact_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.put(f"/contacts/{uuid4()}", json={"first_name": "Jane"})
    assert response.status_code == 404


def test_delete_contact(client, mock_db, sample_contact):
    mock_db.execute.return_value = MockResult([sample_contact])
    response = client.delete(f"/contacts/{sample_contact.id}")
    assert response.status_code == 204
    mock_db.delete.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


def test_delete_contact_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.delete(f"/contacts/{uuid4()}")
    assert response.status_code == 404


def test_import_contacts_csv(client, mock_db):
    csv_content = "first_name,last_name,phone,telegram_user_id,status\nAlice,Wonderland,+1111111111,111,new\nBob,Builder,+2222222222,222,new"
    response = client.post(
        "/contacts/import",
        files={"file": ("contacts.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["first_name"] == "Alice"
    assert data[1]["first_name"] == "Bob"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_contacts_requires_filename(mock_db):
    file = SimpleNamespace(filename="", read=AsyncMock(return_value=b"data"))

    with pytest.raises(Exception) as exc_info:
        await import_contacts(file=file, db=mock_db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Filename is required"


def test_import_contacts_excel(client, mock_db, monkeypatch, sample_contact):
    async def fake_upsert(db, records, source):
        return [sample_contact], []

    monkeypatch.setattr(
        "app.api.contacts.parse_excel",
        lambda contents: [{"first_name": "Excel", "telegram_user_id": 333}],
    )
    monkeypatch.setattr("app.api.contacts.upsert_contacts", fake_upsert)

    response = client.post(
        "/contacts/import",
        files={
            "file": (
                "contacts.xlsx",
                io.BytesIO(b"xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 201


def test_import_contacts_parse_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.contacts.parse_csv",
        lambda contents: (_ for _ in ()).throw(ValueError("bad csv")),
    )

    response = client.post(
        "/contacts/import",
        files={"file": ("contacts.csv", io.BytesIO(b"bad"), "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "bad csv"


def test_import_contacts_invalid_extension(client, mock_db):
    response = client.post(
        "/contacts/import",
        files={"file": ("contacts.txt", io.BytesIO(b"not csv"), "text/plain")},
    )
    assert response.status_code == 400


def test_discover_contacts_enriches_validated_usernames(client, monkeypatch):
    async def fake_discover(criteria, source):
        assert criteria.query == "crm logistics"
        assert criteria.limit == 2
        assert criteria.keywords == ["crm"]
        assert criteria.job_title == "CEO"
        assert criteria.company == "Acme"
        assert source == "telegram_search"
        return [
            DiscoveredContact(
                telegram_username="leaduser",
                telegram_user_id=None,
                first_name=None,
                last_name=None,
                company_name="Acme",
                position="CEO",
                city="Warsaw",
                industry="Logistics",
                bio="Looking for CRM",
                source="telegram_search",
            )
        ]

    async def fake_validate(usernames):
        assert usernames == ["leaduser"]
        return {
            "leaduser": {
                "user_id": 12345,
                "first_name": "Lead",
                "last_name": "User",
            }
        }

    monkeypatch.setattr("app.api.contacts.discover_leads", fake_discover)
    monkeypatch.setattr("app.api.contacts.validate_and_enrich", fake_validate)

    response = client.post(
        "/contacts/discover",
        json={
            "query": "crm logistics",
            "source": "telegram_search",
            "limit": 2,
            "criteria": {
                "keywords": ["crm"],
                "job_title": "CEO",
                "company": "Acme",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data == [
        {
            "telegram_username": "leaduser",
            "telegram_user_id": 12345,
            "first_name": "Lead",
            "last_name": "User",
            "company_name": "Acme",
            "position": "CEO",
            "city": "Warsaw",
            "industry": "Logistics",
            "bio": "Looking for CRM",
            "source": "telegram_search",
            "is_valid": "valid",
        }
    ]


def test_discover_contacts_keeps_preview_when_validation_fails(client, monkeypatch):
    async def fake_discover(criteria, source):
        return [DiscoveredContact(telegram_username="leaduser", first_name="Lead")]

    async def failing_validate(usernames):
        raise RuntimeError("validator unavailable")

    monkeypatch.setattr("app.api.contacts.discover_leads", fake_discover)
    monkeypatch.setattr("app.api.contacts.validate_and_enrich", failing_validate)

    response = client.post("/contacts/discover", json={"query": "crm"})

    assert response.status_code == 200
    data = response.json()
    assert data[0]["telegram_username"] == "leaduser"
    assert data[0]["first_name"] == "Lead"
    assert data[0]["is_valid"] == "unknown"


def test_confirm_discovered_contacts_filters_fields_and_uses_discover_source(
    client, mock_db, sample_contact, monkeypatch
):
    captured = {}

    async def fake_upsert(db, records, source):
        captured["db"] = db
        captured["records"] = records
        captured["source"] = source
        return [sample_contact], []

    monkeypatch.setattr("app.api.contacts.upsert_contacts", fake_upsert)

    response = client.post(
        "/contacts/discover/confirm",
        json={
            "contacts": [
                {
                    "telegram_username": "leaduser",
                    "first_name": "Lead",
                    "source_url": "https://t.me/group/42",
                    "unexpected": "must be ignored",
                }
            ]
        },
    )

    assert response.status_code == 201
    assert response.json()[0]["id"] == str(sample_contact.id)
    assert captured["db"] is mock_db
    assert captured["source"] == "discover"
    assert captured["records"] == [
        {
            "telegram_username": "leaduser",
            "first_name": "Lead",
            "source_url": "https://t.me/group/42",
        }
    ]
