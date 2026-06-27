# Quality Requirement Tests (QRTs)

This document maps each quality requirement defined in [`docs/quality-requirements.md`](quality-requirements.md) to one or more automated quality requirement tests.

An automated QRT is a test that runs in CI, produces deterministic pass/fail output, and is stored in the normal repository test location (`tests/`). For evidence type distinctions see [`docs/testing.md`](testing.md).

---

## QRT-01: Health Endpoint Latency

* **Linked Quality Requirement:** [QR-01](quality-requirements.md#qr-01-response-time-for-data-retrieval)
* **ISO/IEC 25010 Sub-characteristic:** Time behaviour
* **Objective:** Verify that the system responds quickly to a simple health check under normal load.
* **Test Location:** `tests/quality_requirement_tests/test_qrt_latency.py`
* **Automated Scenario:**
  1. Start the FastAPI test client with mocked database and scheduler.
  2. Send 100 sequential GET requests to `/health`.
  3. Record response time for each request.
  4. Assert that 95% of requests complete within 500 ms and all requests succeed (HTTP 200).
* **Evidence Type:** Automated unit/integration test executed in CI.

---

## QRT-02: Health Endpoint Availability

* **Linked Quality Requirement:** [QR-02](quality-requirements.md#qr-02-core-system-availability)
* **ISO/IEC 25010 Sub-characteristic:** Availability
* **Objective:** Provide an automated proxy for the long-term availability SLO.
* **Test Location:** `tests/quality_requirement_tests/test_qrt_availability.py`
* **Automated Scenario:**
  1. Start the FastAPI test client with mocked database and a running scheduler.
  2. Send GET `/health`.
  3. Assert HTTP 200 OK with `status` equal to `"ok"`.
  4. Simulate a scheduler failure and assert the endpoint still returns HTTP 200 with `status` equal to `"degraded"`.
* **Evidence Type:** Automated integration test executed in CI.

---

## QRT-03: API Fault Tolerance on Invalid Input

* **Linked Quality Requirement:** [QR-03](quality-requirements.md#qr-03-api-fault-tolerance)
* **ISO/IEC 25010 Sub-characteristic:** Fault tolerance
* **Objective:** Verify that the API rejects malformed JSON without crashing and returns a descriptive 400 Bad Request quickly.
* **Test Location:** `tests/quality_requirement_tests/test_qrt_fault_tolerance.py`
* **Automated Scenario:**
  1. Start the FastAPI test client.
  2. POST invalid JSON (e.g., malformed body or missing required fields) to `/contacts`.
  3. Assert HTTP 400 Bad Request.
  4. Assert response time ≤ 200 ms.
* **Evidence Type:** Automated integration test executed in CI.

---

## Running the QRTs

```bash
pytest tests/quality_requirement_tests/ -v
```

The QRTs are included in the default test command used by CI:

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```
