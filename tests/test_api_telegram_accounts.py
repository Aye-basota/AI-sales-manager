"""Tests for the telegram-accounts API."""

from uuid import uuid4
from datetime import datetime

import pytest

from tests.conftest import MockResult
from app.models.telegram_account import TelegramAccount


@pytest.fixture
def sample_account():
    return TelegramAccount(
        id=uuid4(),
        phone="+79991234567",
        username="seller_demo",
        session_string="plain_session_string",
        status="ready",
        daily_messages_sent=0,
        created_at=datetime.now(),
    )


class TestListTelegramAccounts:
    def test_list_accounts(self, client, mock_db, sample_account):
        mock_db.execute.return_value = MockResult([sample_account])
        response = client.get("/telegram-accounts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["phone"] == "+79991234567"
        assert "session_string" not in data[0]


class TestGetTelegramAccount:
    def test_get_account(self, client, mock_db, sample_account):
        mock_db.execute.return_value = MockResult([sample_account])
        response = client.get(f"/telegram-accounts/{sample_account.id}")
        assert response.status_code == 200
        assert response.json()["phone"] == "+79991234567"

    def test_get_account_not_found(self, client, mock_db):
        mock_db.execute.return_value = MockResult([])
        response = client.get(f"/telegram-accounts/{uuid4()}")
        assert response.status_code == 404


class TestCreateTelegramAccount:
    def test_create_account(self, client, mock_db):
        payload = {
            "phone": "+79991234567",
            "username": "seller_demo",
            "session_string": "plain_session_string",
            "status": "ready",
        }
        response = client.post("/telegram-accounts", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["phone"] == "+79991234567"
        assert data["status"] == "ready"
        assert "session_string" not in data
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    def test_create_account_encrypts_session_when_key_set(
        self, client, mock_db, monkeypatch
    ):
        monkeypatch.setenv("SESSION_ENCRYPTION_KEY", "")
        payload = {
            "phone": "+79991234567",
            "session_string": "plain_session_string",
            "status": "ready",
        }
        response = client.post("/telegram-accounts", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "session_string" not in data


class TestUpdateTelegramAccount:
    def test_update_account(self, client, mock_db, sample_account):
        mock_db.execute.return_value = MockResult([sample_account])
        payload = {"status": "active"}
        response = client.put(f"/telegram-accounts/{sample_account.id}", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        mock_db.commit.assert_awaited_once()

    def test_update_account_not_found(self, client, mock_db):
        mock_db.execute.return_value = MockResult([])
        response = client.put(
            f"/telegram-accounts/{uuid4()}", json={"status": "active"}
        )
        assert response.status_code == 404


class TestDeleteTelegramAccount:
    def test_delete_account(self, client, mock_db, sample_account):
        mock_db.execute.return_value = MockResult([sample_account])
        response = client.delete(f"/telegram-accounts/{sample_account.id}")
        assert response.status_code == 204
        mock_db.delete.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    def test_delete_account_not_found(self, client, mock_db):
        mock_db.execute.return_value = MockResult([])
        response = client.delete(f"/telegram-accounts/{uuid4()}")
        assert response.status_code == 404
