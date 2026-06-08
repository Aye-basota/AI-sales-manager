from uuid import uuid4
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
