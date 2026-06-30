# Quality Requirement Tests (QRTs)

This document maps each quality requirement defined in [`docs/quality-requirements.md`](quality-requirements.md) to one or more automated quality requirement tests.

An automated QRT is a test that runs in CI, produces deterministic pass/fail output, and is stored in the normal repository test location (`tests/`). For evidence type distinctions see [`docs/testing.md`](testing.md).

---

## QRT-001: Health Endpoint Response Time

* **Linked quality requirement:** [QR-001](quality-requirements.md#qr-001-health-endpoint-response-time)
* **Related ADR:** [ADR-001 — Async health check design](architecture/adr/ADR-001.md)
* **Verification method:** Automated integration test using FastAPI `TestClient`.
* **Test data, setup, or environment:** FastAPI test client with mocked database and scheduler. 100 sequential GET `/health` requests.
* **Automated command or CI check:** `pytest tests/quality_requirement_tests/test_qrt_latency.py -v`
* **Expected measurable result:** All 100 requests return HTTP `200 OK` and the 95th percentile response time is ≤ 500 ms.
* **Evidence location:** Latest protected-default-branch CI run and local coverage report.

---

## QRT-002: Core System Availability Proxy

* **Linked quality requirement:** [QR-002](quality-requirements.md#qr-002-core-system-availability-proxy)
* **Related ADR:** [ADR-002 — Scheduler health integration](architecture/adr/ADR-002.md)
* **Verification method:** Automated integration test using FastAPI `TestClient`.
* **Test data, setup, or environment:** FastAPI test client with mocked database and a mocked scheduler running state.
* **Automated command or CI check:** `pytest tests/quality_requirement_tests/test_qrt_availability.py -v`
* **Expected measurable result:**
  * Scheduler running → HTTP `200 OK`, `status` is `"ok"`, `scheduler` is `true`.
  * Scheduler not running → HTTP `200 OK`, `status` is `"degraded"`, `scheduler` is `false`.
* **Evidence location:** Latest protected-default-branch CI run and local coverage report.

---

## QRT-003: API Fault Tolerance on Invalid Input

* **Linked quality requirement:** [QR-003](quality-requirements.md#qr-003-api-fault-tolerance-on-invalid-input)
* **Related ADR:** [ADR-003 — Global exception handling](architecture/adr/ADR-003.md)
* **Verification method:** Automated integration test using FastAPI `TestClient`.
* **Test data, setup, or environment:** FastAPI test client. POST requests with malformed JSON and with missing required fields.
* **Automated command or CI check:** `pytest tests/quality_requirement_tests/test_qrt_fault_tolerance.py -v`
* **Expected measurable result:**
  * Malformed JSON returns HTTP `400 Bad Request` within 200 ms.
  * Missing required field returns HTTP `400 Bad Request`.
* **Evidence location:** Latest protected-default-branch CI run and local coverage report.

---

## Running the QRTs

```bash
# QRTs only
pytest tests/quality_requirement_tests/ -v

# Full test suite including QRTs, unit tests, and integration tests
pytest tests/ -v --cov=app --cov-report=term-missing
```

The QRTs are included in the default test command used by CI:

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## MVP v2 Quality Requirement Tests

As `MVP v2` features are implemented, add new automated QRTs here. Each new QRT must have a stable `QRT-NNN` ID, a linked quality requirement, and a related ADR where applicable.
