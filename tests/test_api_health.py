"""Tests for the health endpoint."""

from unittest.mock import patch


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        with patch("app.api.health.scheduler.is_running", return_value=True):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["scheduler"] is True
        assert data["db"] is True

    def test_health_degraded_when_db_fails(self, client, mock_db):
        mock_db.execute.side_effect = Exception("DB down")
        with patch("app.api.health.scheduler.is_running", return_value=True):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["db"] is False
        assert data["scheduler"] is True

    def test_health_scheduler_not_running(self, client):
        with patch("app.api.health.scheduler.is_running", return_value=False):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["scheduler"] is False
