"""QRT-02: Health endpoint availability proxy."""

from unittest.mock import patch


class TestQRT02HealthAvailability:
    """Verify /health returns 200 OK when services are healthy."""

    def test_health_available_when_healthy(self, client):
        with patch("app.api.health.scheduler.is_running", return_value=True):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["scheduler"] is True
        assert data["db"] is True

    def test_health_degraded_but_available_when_scheduler_fails(self, client):
        with patch("app.api.health.scheduler.is_running", return_value=False):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["scheduler"] is False
