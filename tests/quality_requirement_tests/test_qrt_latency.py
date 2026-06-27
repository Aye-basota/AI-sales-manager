"""QRT-001: Health endpoint latency under normal load."""

import time
from unittest.mock import patch


class TestQRT01HealthLatency:
    """Verify 95th percentile response time for /health is ≤ 500 ms."""

    def test_health_latency_95th_percentile(self, client):
        with patch("app.api.health.scheduler.is_running", return_value=True):
            times = []
            for _ in range(100):
                start = time.perf_counter()
                response = client.get("/health")
                elapsed_ms = (time.perf_counter() - start) * 1000
                times.append(elapsed_ms)
                assert response.status_code == 200

        times.sort()
        p95 = times[94]  # 95th percentile for 100 samples (0-indexed)
        assert p95 <= 500, f"95th percentile latency {p95:.2f} ms exceeds 500 ms"
