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

## Running the QRTs

```bash
# QRTs only (run through their respective test modules)
pytest tests/test_llm_guardrails.py tests/test_core_state_machine.py tests/test_core_scheduler.py -v

# Full test suite including QRTs
pytest tests/ -v --cov=app --cov-report=term-missing
```

The QRTs are included in the default test command used by CI.
