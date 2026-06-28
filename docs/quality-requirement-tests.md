# Quality Requirement Tests — AI Sales Manager

This document links each quality requirement to its automated test evidence.
All tests run in CI via `pytest tests/ -v --cov=app`.

See [`docs/quality-requirements.md`](quality-requirements.md) for the full quality requirement scenarios.

---

## QRT-01: LLM Guardrails Block Forbidden Content

**Linked QR:** [QR-01](quality-requirements.md#qr-01-llm-response-safety-security--confidentiality)
**Test file:** [`tests/test_llm_guardrails.py`](../tests/test_llm_guardrails.py)
**Evidence type:** Automated unit tests (pytest)
**CI job:** `test` job in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

### What is tested

| Test | What it verifies |
|---|---|
| `test_check_length_exceeds_limit` | Messages over 300 words are blocked |
| `test_check_no_forbidden_topics_default` | Messages containing politics/religion keywords are blocked |
| `test_check_no_forbidden_topics_custom` | Custom forbidden topic lists work correctly |
| `test_apply_guardrails_passes` | Clean messages pass through unchanged |
| `test_apply_guardrails_fails_length` | Oversized messages return `None` |
| `test_check_no_bot_words` | Messages containing "бот", "ассистент" are blocked |
| `test_check_no_markdown` | Messages with `#`, `*`, `_`, backtick are blocked |
| `evaluate_guardrails_*` | Full guardrail pipeline returns structured `GuardrailsResult` |

### How to run

```bash
pytest tests/test_llm_guardrails.py -v
```

### Pass criteria

All tests pass. No forbidden content reaches `SellerClient.send_message()`.

---

## QRT-02: State Machine Correctness and Terminal State Immutability

**Linked QR:** [QR-02](quality-requirements.md#qr-02-conversation-state-correctness-reliability--fault-tolerance)
**Test file:** [`tests/test_core_state_machine.py`](../tests/test_core_state_machine.py)
**Evidence type:** Automated unit tests (pytest)
**CI job:** `test` job in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

### What is tested

| Test | What it verifies |
|---|---|
| `test_cold_to_warm_on_initial_message` | Initial message moves state from cold → warm |
| `test_cold_to_meeting_booked_on_meeting_intent` | Meeting intent triggers terminal state directly |
| `test_meeting_booked_is_terminal_no_transition` | No event can exit `meeting_booked` |
| `test_closed_is_terminal_no_transition` | No event can exit `closed` |
| `test_unknown_event_returns_current_state` | Unknown events are safely ignored |
| `test_unknown_state_returns_current_state` | Unknown states do not cause exceptions |
| `TestIsTerminal.*` | `is_terminal()` correctly identifies terminal states |

### How to run

```bash
pytest tests/test_core_state_machine.py -v
```

### Pass criteria

All 22 test cases pass. Coverage of `app/core/state_machine.py` is 100%.

---

## QRT-03: Scheduler Account Selection and Contact Filtering

**Linked QR:** [QR-03](quality-requirements.md#qr-03-outbound-message-delivery-performance-performance-efficiency--time-behaviour)
**Test file:** [`tests/test_core_scheduler.py`](../tests/test_core_scheduler.py)
**Evidence type:** Automated unit/integration tests with mocked Pyrogram and LLM (pytest + AsyncMock)
**CI job:** `test` job in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

### What is tested

| Test area | What it verifies |
|---|---|
| Account selection | Only `ready`/`active` accounts under daily limit are selected |
| Rate limit enforcement | Accounts with last message < 30 s ago are skipped |
| Working hours filter | Contacts outside campaign timezone window are skipped |
| Follow-up delay | Contacts messaged less than 24 h ago are skipped |
| Cooldown handling | Accounts in cooldown are not selected |
| Daily reset | `daily_messages_sent` resets to 0 at 00:00 MSK |

### How to run

```bash
pytest tests/test_core_scheduler.py -v
```

### Pass criteria

All scheduler tests pass. Account selection completes without raising exceptions for all account states.

---

## QRT-04: Anti-Repetition Check

**Linked QR:** [QR-04](quality-requirements.md#qr-04-anti-repetition-in-generated-messages-usability--user-error-protection)
**Test file:** [`tests/test_llm_guardrails.py`](../tests/test_llm_guardrails.py)
**Evidence type:** Automated unit tests (pytest)
**CI job:** `test` job in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

### What is tested

| Test | What it verifies |
|---|---|
| `test_check_anti_repetition_no_history` | Empty history always passes |
| `test_check_anti_repetition_similar` | Identical message against history is blocked (similarity = 1.0 ≥ 0.8) |
| `test_check_anti_repetition_different` | Distinct message against history passes |

### How to run

```bash
pytest tests/test_llm_guardrails.py -k "repetition" -v
```

### Pass criteria

Similar messages (Levenshtein ≥ 0.8) are always blocked. Distinct messages are always passed.

---

## Running All QRTs Together

```bash
pytest tests/test_llm_guardrails.py tests/test_core_state_machine.py tests/test_core_scheduler.py -v
```

Expected: all tests pass. CI must show a green status for all QRT files before a PR/MR can be merged.
