import io
from uuid import uuid4
from tests.conftest import MockResult


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


def test_import_contacts_invalid_extension(client, mock_db):
    response = client.post(
        "/contacts/import",
        files={"file": ("contacts.txt", io.BytesIO(b"not csv"), "text/plain")},
    )
    assert response.status_code == 400
