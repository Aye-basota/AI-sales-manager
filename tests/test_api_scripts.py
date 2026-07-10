from uuid import uuid4
from tests.conftest import MockResult


def test_list_scripts(client, mock_db, sample_script):
    mock_db.execute.return_value = MockResult([sample_script])
    response = client.get("/scripts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Script"


def test_list_scripts_normalizes_legacy_nullable_fields(client, mock_db, sample_script):
    sample_script.sales_funnel = {}
    sample_script.first_message_goal = None
    sample_script.call_to_action = None
    sample_script.language = None
    sample_script.emoji_policy = None
    sample_script.max_first_message_length = None
    mock_db.execute.return_value = MockResult([sample_script])

    response = client.get("/scripts")

    assert response.status_code == 200
    data = response.json()[0]
    assert data["sales_funnel"] == []
    assert data["first_message_goal"] == "trust"
    assert data["call_to_action"] == "15-минутный созвон"
    assert data["language"] == "ru"
    assert data["emoji_policy"] == "forbidden"
    assert data["max_first_message_length"] == 200


def test_get_script(client, mock_db, sample_script):
    mock_db.execute.return_value = MockResult([sample_script])
    response = client.get(f"/scripts/{sample_script.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Script"


def test_get_script_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.get(f"/scripts/{uuid4()}")
    assert response.status_code == 404


def test_create_script(client, mock_db):
    payload = {
        "name": "New Script",
        "role_prompt": "You are a bot",
        "goal": "Sell stuff",
        "working_hours_start": "09:00:00",
        "working_hours_end": "18:00:00",
    }
    response = client.post("/scripts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Script"
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


def test_update_script(client, mock_db, sample_script):
    mock_db.execute.return_value = MockResult([sample_script])
    payload = {"name": "Updated Script"}
    response = client.put(f"/scripts/{sample_script.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Script"
    mock_db.commit.assert_awaited_once()


def test_update_script_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.put(f"/scripts/{uuid4()}", json={"name": "Updated"})
    assert response.status_code == 404


def test_delete_script(client, mock_db, sample_script):
    mock_db.execute.return_value = MockResult([sample_script])
    response = client.delete(f"/scripts/{sample_script.id}")
    assert response.status_code == 204
    mock_db.delete.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


def test_delete_script_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.delete(f"/scripts/{uuid4()}")
    assert response.status_code == 404
