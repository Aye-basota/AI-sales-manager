# Quality Requirements — AI Sales Manager

This document defines quality requirements using ISO/IEC 25010 quality sub-characteristics.
Each requirement uses the measurable scenario format: stimulus → response → measurable outcome.

Each relevant quality requirement links to the architecture decision(s) that address it (see [`docs/architecture/adr/`](architecture/adr/)) and to automated quality requirement tests in [`docs/quality-requirement-tests.md`](quality-requirement-tests.md).

| ID | Sub-characteristic | Related ADR |
|---|---|---|
| [QR-01](#qr-01) | Confidentiality (Security) | [ADR-001](architecture/adr/ADR-001.md) |
| [QR-02](#qr-02) | Fault Tolerance (Reliability) | [ADR-002](architecture/adr/ADR-002.md) |
| [QR-03](#qr-03) | Time Behaviour (Performance Efficiency) | [ADR-003](architecture/adr/ADR-003.md) |
| [QR-04](#qr-04) | User Error Protection (Usability) | [ADR-004](architecture/adr/ADR-004.md) |

---

<a id="qr-01"></a>
## QR-01: LLM Response Safety (Security — Confidentiality)

**ID:** QR-01
**ISO/IEC 25010 sub-characteristic:** Confidentiality (Security)
**Rationale:** The system generates outbound messages on behalf of real Telegram accounts. A message that contains forbidden topics (politics, religion, hate speech, bot self-identification) can damage the client's brand, expose legal liability, or trigger Telegram account bans. Guardrails must block such content before delivery.

### Scenario

| Field | Value |
|---|---|
| **Stimulus** | LLM returns a response containing a forbidden topic keyword, a markdown symbol, CJK/Arabic characters, or the word "бот" (bot) |
| **Response** | `apply_guardrails()` returns `None`; the message is not sent; the system retries generation |
| **Measurable outcome** | 100% of guardrail-violating messages are blocked in automated tests; no forbidden content reaches `SellerClient.send_message()` |

**Linked tests:** `tests/test_llm_guardrails.py`
**Related ADR:** [ADR-001 — LLM Output Guardrails](architecture/adr/ADR-001.md)

---

<a id="qr-02"></a>
## QR-02: Conversation State Correctness (Reliability — Fault Tolerance)

**ID:** QR-02
**ISO/IEC 25010 sub-characteristic:** Fault Tolerance (Reliability)
**Rationale:** The sales funnel depends on deterministic state transitions. An incorrect transition (e.g., moving a `meeting_booked` lead back to `warm`) corrupts the funnel, sends messages to closed leads, and inflates analytics. The state machine must produce correct outputs for all defined inputs and must be immutable — terminal states must never be exited.

### Scenario

| Field | Value |
|---|---|
| **Stimulus** | Any event is applied to any conversation state, including terminal states (`meeting_booked`, `closed`) and unknown states |
| **Response** | `transition(state, event)` returns the correct next state; terminal states return themselves for any event; unknown states/events return the current state unchanged |
| **Measurable outcome** | 100% branch coverage on `app/core/state_machine.py`; all 22 test cases in `test_core_state_machine.py` pass |

**Linked tests:** `tests/test_core_state_machine.py`
**Related ADR:** [ADR-002 — Deterministic Conversation State Machine](architecture/adr/ADR-002.md)

---

<a id="qr-03"></a>
## QR-03: Outbound Message Delivery Performance (Performance Efficiency — Time Behaviour)

**ID:** QR-03
**ISO/IEC 25010 sub-characteristic:** Time Behaviour (Performance Efficiency)
**Rationale:** The system processes campaigns every 5 minutes. If account selection, LLM generation, or message dispatch takes longer than the scheduler interval, jobs stack up, duplicate messages are sent, and daily limits are exceeded. The critical path from scheduler tick to message sent must complete within a bounded time.

### Scenario

| Field | Value |
|---|---|
| **Stimulus** | APScheduler fires `process_campaigns()` for a campaign with 10 pending contacts and 3 available Telegram accounts |
| **Response** | The scheduler selects accounts, generates messages, and dispatches all pending contacts within the cycle |
| **Measurable outcome** | Scheduler unit tests mock LLM and Pyrogram and assert all contacts are processed without timeout; account selection logic completes in < 1 ms per contact in unit tests |

**Linked tests:** `tests/test_core_scheduler.py`
**Related ADR:** [ADR-003 — Scheduler-Driven Outbound Processing](architecture/adr/ADR-003.md)

---

<a id="qr-04"></a>
## QR-04: Anti-Repetition in Generated Messages (Usability — User Error Protection)

**ID:** QR-04
**ISO/IEC 25010 sub-characteristic:** User Error Protection (Usability)
**Rationale:** Sending the same or near-identical message twice to the same lead signals automation, damages trust, and may trigger Telegram spam filters. The guardrails must detect Levenshtein similarity ≥ 0.8 with any of the last 5 messages and reject the repeated output.

### Scenario

| Field | Value |
|---|---|
| **Stimulus** | LLM generates a message with cosine/Levenshtein similarity ≥ 0.8 to one of the last 5 outbound messages in the same conversation |
| **Response** | `check_anti_repetition()` returns `False`; `apply_guardrails()` returns `None`; generation is retried |
| **Measurable outcome** | Automated test confirms repetition check blocks similar messages and passes distinct messages; threshold 0.8 is tested with boundary values |

**Linked tests:** `tests/test_llm_guardrails.py` (`test_check_anti_repetition_*`)
**Related ADR:** [ADR-004 — Anti-Repetition Check for Generated Messages](architecture/adr/ADR-004.md)
