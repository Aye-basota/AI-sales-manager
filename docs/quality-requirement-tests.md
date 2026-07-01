# Quality Requirement Tests (QRTs)

This document maps each quality requirement defined in [`docs/quality-requirements.md`](quality-requirements.md) to one or more automated quality requirement tests.

An automated QRT is a test that runs in CI, produces deterministic pass/fail output, and is stored in the normal repository test location (`tests/`).

---

## QRT-01: LLM Response Safety

* **Linked quality requirement:** [QR-01](quality-requirements.md#qr-01)
* **Related ADR:** [ADR-001 — LLM Output Guardrails](architecture/adr/ADR-001.md)
* **Verification method:** Automated unit tests for `app/llm/guardrails.py`.
* **Test data, setup, or environment:** Standard pytest environment with fixture inputs containing forbidden topics, markdown, CJK/Arabic characters, and bot self-identification.
* **Automated command or CI check:** `pytest tests/test_llm_guardrails.py -v`
* **Expected measurable result:** 100% of guardrail-violating inputs are rejected; valid inputs pass.
* **Evidence location:** Latest protected-default-branch CI run.

---

## QRT-02: Conversation State Correctness

* **Linked quality requirement:** [QR-02](quality-requirements.md#qr-02)
* **Related ADR:** [ADR-002 — Deterministic Conversation State Machine](architecture/adr/ADR-002.md)
* **Verification method:** Automated unit tests for `app/core/state_machine.py`.
* **Test data, setup, or environment:** Standard pytest environment covering all defined states, events, terminal states, and unknown inputs.
* **Automated command or CI check:** `pytest tests/test_core_state_machine.py -v`
* **Expected measurable result:** All state transitions are correct; terminal states are immutable; 100% branch coverage.
* **Evidence location:** Latest protected-default-branch CI run.

---

## QRT-03: Outbound Message Delivery Performance

* **Linked quality requirement:** [QR-03](quality-requirements.md#qr-03)
* **Related ADR:** [ADR-003 — Scheduler-Driven Outbound Processing](architecture/adr/ADR-003.md)
* **Verification method:** Automated integration tests for `app/core/scheduler.py` with mocked LLM and Pyrogram.
* **Test data, setup, or environment:** Standard pytest environment with a campaign containing multiple pending contacts and available accounts.
* **Automated command or CI check:** `pytest tests/test_core_scheduler.py -v`
* **Expected measurable result:** All pending contacts are processed without timeout; account selection logic completes in < 1 ms per contact in unit tests.
* **Evidence location:** Latest protected-default-branch CI run.

---

## QRT-04: Anti-Repetition in Generated Messages

* **Linked quality requirement:** [QR-04](quality-requirements.md#qr-04)
* **Related ADR:** [ADR-004 — Anti-Repetition Check for Generated Messages](architecture/adr/ADR-004.md)
* **Verification method:** Automated unit tests for `app/llm/guardrails.py` anti-repetition logic.
* **Test data, setup, or environment:** Standard pytest environment with messages at and around the 0.8 similarity threshold.
* **Automated command or CI check:** `pytest tests/test_llm_guardrails.py::test_check_anti_repetition -v`
* **Expected measurable result:** Similar messages (≥ 0.8) are rejected; distinct messages pass.
* **Evidence location:** Latest protected-default-branch CI run.

---

## QRT-05: Prompt Configuration Maintainability

* **Linked quality requirement:** [QR-05](quality-requirements.md#qr-05)
* **Related ADR:** [ADR-005 — External Prompt Configuration and Versioning](architecture/adr/ADR-005.md)
* **Verification method:** Unit tests for `app.config.prompts.load_prompt_config()` and prompt builders.
* **Test data, setup, or environment:** Standard pytest environment with the default `app/config/prompts/v1.json`.
* **Automated command or CI check:** `pytest tests/test_llm_prompts.py tests/test_llm_funnel_prompts.py -v`
* **Expected measurable result:** Prompt config loads without errors; system/reply/follow-up prompts render expected stage-specific content.
* **Evidence location:** Latest protected-default-branch CI run.

---

## QRT-06: Funnel Definition Validity

* **Linked quality requirement:** [QR-06](quality-requirements.md#qr-06)
* **Related ADR:** [ADR-006 — Funnel Upload and Preview API](architecture/adr/ADR-006.md)
* **Verification method:** Integration tests for `POST /api/funnels/preview` and `POST /api/funnels/upload`.
* **Test data, setup, or environment:** Standard pytest environment with valid/invalid JSON and plain-text funnel payloads.
* **Automated command or CI check:** `pytest tests/test_api_funnels.py -v`
* **Expected measurable result:** Invalid funnels return HTTP 422; valid funnels are accepted with normalized stages.
* **Evidence location:** Latest protected-default-branch CI run.

---

## QRT-07: Production Health Observability

* **Linked quality requirement:** [QR-07](quality-requirements.md#qr-07)
* **Related ADR:** [ADR-007 — Production Monitoring and Logging](architecture/adr/ADR-007.md)
* **Verification method:** Integration test for `GET /health`.
* **Test data, setup, or environment:** Standard pytest environment with mocked database and scheduler.
* **Automated command or CI check:** `pytest tests/test_api_health.py -v`
* **Expected measurable result:** Endpoint returns `status`, `db`, and `scheduler` fields within 500 ms; degraded state reported when DB or scheduler is down.
* **Evidence location:** Latest protected-default-branch CI run.

---

## QRT-08: AI Automation Rate Accuracy

* **Linked quality requirement:** [QR-08](quality-requirements.md#qr-08)
* **Related ADR:** [ADR-008 — AI-Automation Rate Tracking](architecture/adr/ADR-008.md)
* **Verification method:** Integration tests for `GET /analytics/automation-rate` and conversation status updates.
* **Test data, setup, or environment:** Standard pytest environment with mocked `Conversation` counts and status-change scenarios.
* **Automated command or CI check:** `pytest tests/test_api_analytics.py tests/test_api_conversations.py -v`
* **Expected measurable result:** Rate endpoint returns correct `ai_handled`, `escalated`, and `rate_pct`; status updates mark conversations as escalated.
* **Evidence location:** Latest protected-default-branch CI run.

---

## Running the QRTs

```bash
# QRTs only (run through their respective test modules)
pytest tests/test_llm_guardrails.py tests/test_core_state_machine.py tests/test_core_scheduler.py tests/test_llm_prompts.py tests/test_api_funnels.py tests/test_api_health.py tests/test_api_analytics.py tests/test_api_conversations.py -v

# Full test suite including QRTs
pytest tests/ -v --cov=app --cov-report=term-missing
```

The QRTs are included in the default test command used by CI.
