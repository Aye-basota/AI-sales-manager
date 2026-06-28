from uuid import uuid4
from app.models.campaign import CampaignContact
from tests.conftest import MockResult


def test_list_campaigns(client, mock_db, sample_campaign):
    mock_db.execute.return_value = MockResult([sample_campaign])
    response = client.get("/campaigns")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Campaign"


def test_get_campaign(client, mock_db, sample_campaign):
    mock_db.execute.return_value = MockResult([sample_campaign])
    response = client.get(f"/campaigns/{sample_campaign.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Campaign"


def test_get_campaign_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.get(f"/campaigns/{uuid4()}")
    assert response.status_code == 404


def test_create_campaign(client, mock_db):
    payload = {
        "name": "New Campaign",
        "status": "draft",
    }
    response = client.post("/campaigns", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Campaign"
    mock_db.commit.assert_awaited_once()


def test_update_campaign_status(client, mock_db, sample_campaign):
    mock_db.execute.return_value = MockResult([sample_campaign])
    payload = {"status": "running"}
    response = client.put(f"/campaigns/{sample_campaign.id}/status", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    mock_db.commit.assert_awaited_once()


def test_update_campaign_status_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.put(f"/campaigns/{uuid4()}/status", json={"status": "running"})
    assert response.status_code == 404


def test_delete_campaign(client, mock_db, sample_campaign):
    mock_db.execute.return_value = MockResult([sample_campaign])
    response = client.delete(f"/campaigns/{sample_campaign.id}")
    assert response.status_code == 204
    mock_db.delete.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


def test_delete_campaign_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.delete(f"/campaigns/{uuid4()}")
    assert response.status_code == 404


def test_add_contacts_to_campaign(client, mock_db, sample_campaign, sample_contact):
    mock_db.execute.return_value = MockResult([sample_campaign])
    payload = {"contact_ids": [str(sample_contact.id), str(uuid4())]}
    response = client.post(f"/campaigns/{sample_campaign.id}/contacts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["status"] == "pending"
    assert data[0]["campaign_id"] == str(sample_campaign.id)
    assert mock_db.add.call_count == 2
    mock_db.commit.assert_awaited_once()
    assert mock_db.refresh.await_count == 2


def test_add_contacts_to_campaign_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.post(
        f"/campaigns/{uuid4()}/contacts", json={"contact_ids": [str(uuid4())]}
    )
    assert response.status_code == 404


def test_start_campaign(client, mock_db, sample_campaign):
    sample_campaign.status = "draft"
    mock_db.execute.return_value = MockResult([sample_campaign])
    response = client.post(f"/campaigns/{sample_campaign.id}/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert sample_campaign.started_at is not None
    mock_db.commit.assert_awaited_once()


def test_start_campaign_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.post(f"/campaigns/{uuid4()}/start")
    assert response.status_code == 404


def test_start_campaign_invalid_status(client, mock_db, sample_campaign):
    sample_campaign.status = "running"
    mock_db.execute.return_value = MockResult([sample_campaign])
    response = client.post(f"/campaigns/{sample_campaign.id}/start")
    assert response.status_code == 400


def test_stop_campaign(client, mock_db, sample_campaign):
    sample_campaign.status = "running"
    mock_db.execute.return_value = MockResult([sample_campaign])
    response = client.post(f"/campaigns/{sample_campaign.id}/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"
    mock_db.commit.assert_awaited_once()


def test_stop_campaign_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.post(f"/campaigns/{uuid4()}/stop")
    assert response.status_code == 404


def test_stop_campaign_invalid_status(client, mock_db, sample_campaign):
    sample_campaign.status = "draft"
    mock_db.execute.return_value = MockResult([sample_campaign])
    response = client.post(f"/campaigns/{sample_campaign.id}/stop")
    assert response.status_code == 400


def test_list_campaign_contacts(client, mock_db, sample_campaign, sample_contact):
    campaign_contact = CampaignContact(
        id=uuid4(),
        campaign_id=sample_campaign.id,
        contact_id=sample_contact.id,
        status="pending",
        message_count=0,
    )
    mock_db.execute.side_effect = [
        MockResult([sample_campaign]),
        MockResult([(sample_contact, campaign_contact)]),
    ]
    response = client.get(f"/campaigns/{sample_campaign.id}/contacts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["contact_id"] == str(sample_contact.id)
    assert data[0]["first_name"] == sample_contact.first_name
    assert data[0]["status"] == "pending"


def test_list_campaign_contacts_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.get(f"/campaigns/{uuid4()}/contacts")
    assert response.status_code == 404


def test_list_campaign_contacts_empty(client, mock_db, sample_campaign):
    mock_db.execute.side_effect = [
        MockResult([sample_campaign]),
        MockResult([]),
    ]
    response = client.get(f"/campaigns/{sample_campaign.id}/contacts")
    assert response.status_code == 200
    data = response.json()
    assert data == []
