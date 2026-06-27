"""QRT-03: API fault tolerance on invalid input."""

import time


class TestQRT03FaultTolerance:
    """Verify API returns 400 Bad Request quickly for invalid JSON."""

    def test_invalid_json_returns_400_within_200ms(self, client):
        start = time.perf_counter()
        response = client.post(
            "/contacts",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 400
        assert elapsed_ms <= 200, f"Fault tolerance response took {elapsed_ms:.2f} ms"

    def test_missing_required_fields_returns_400(self, client):
        # Telegram account creation requires 'phone'.
        response = client.post(
            "/telegram-accounts",
            json={"username": "seller"},  # missing required 'phone'
        )
        assert response.status_code == 400
