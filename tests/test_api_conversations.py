from uuid import uuid4
from tests.conftest import MockResult


def test_list_conversations(client, mock_db, sample_conversation):
    mock_db.execute.return_value = MockResult([sample_conversation])
    response = client.get("/conversations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["current_state"] == "cold"


def test_get_conversation_messages(client, mock_db, sample_message):
    mock_db.execute.return_value = MockResult([sample_message])
    response = client.get(f"/conversations/{sample_message.conversation_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello"


def test_update_conversation_status(client, mock_db, sample_conversation):
    mock_db.execute.return_value = MockResult([sample_conversation])
    payload = {"operator_status": "resolved", "operator_notes": "Done"}
    response = client.put(
        f"/conversations/{sample_conversation.id}/status", json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["operator_status"] == "resolved"
    mock_db.commit.assert_awaited_once()


def test_update_conversation_status_not_found(client, mock_db):
    mock_db.execute.return_value = MockResult([])
    response = client.put(
        f"/conversations/{uuid4()}/status", json={"operator_status": "resolved"}
    )
    assert response.status_code == 404
