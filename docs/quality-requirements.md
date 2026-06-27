# Quality Requirements

This document defines the measurable quality requirements for the AI Sales Manager product. Each requirement uses a stable ID, an ISO/IEC 25010 sub-characteristic, a measurable scenario, and links to automated quality requirement tests.

## QR-001: Health Endpoint Response Time

* **ISO/IEC 25010 sub-characteristic:** Time behaviour
* **Scenario:** When an API client sends a GET request to the `/health` endpoint under normal load conditions with the scheduler running, the system shall return a complete `200 OK` response within 500 milliseconds for at least 95% of requests.
* **Why this matters:** Users and external health monitors need fast feedback about system liveness. Slow health checks can hide outages and trigger false alarms.
* **Linked quality requirement tests:** [QRT-001](quality-requirement-tests.md#qrt-001-health-endpoint-response-time)

## QR-002: Core System Availability Proxy

* **ISO/IEC 25010 sub-characteristic:** Availability
* **Scenario:** When the APScheduler task is running under normal operation, the `/health` endpoint shall return HTTP `200 OK` with status `"ok"`; when the scheduler is not running, the endpoint shall still return HTTP `200 OK` with status `"degraded"` within 200 milliseconds.
* **Why this matters:** The application must remain inspectable even when background scheduling is unavailable, so operators can distinguish total outage from partial degradation.
* **Linked quality requirement tests:** [QRT-002](quality-requirement-tests.md#qrt-002-core-system-availability-proxy)

## QR-003: API Fault Tolerance on Invalid Input

* **ISO/IEC 25010 sub-characteristic:** Fault tolerance
* **Scenario:** When the API receives a POST request with invalid or missing required JSON fields under normal operation, the system shall not crash but shall return a `400 Bad Request` response with a descriptive error message within 200 milliseconds.
* **Why this matters:** The backend integrates with frontends and third-party systems that may send malformed payloads. Graceful rejection prevents cascading failures and improves debuggability.
* **Linked quality requirement tests:** [QRT-003](quality-requirement-tests.md#qrt-003-api-fault-tolerance-on-invalid-input)
