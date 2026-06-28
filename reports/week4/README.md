# Week 4 Report — AI Sales Manager

## Project Description

AI Sales Manager is an automated B2B outbound sales system that conducts human-like Telegram conversations using live Telegram accounts (MTProto/Pyrogram) and LLM-generated responses. It autonomously manages a sales funnel from initial contact through follow-up to meeting booking, notifying operators about hot leads in real time.

---

## Sprint Overview

| Field | Value |
|---|---|
| **Sprint Goal** | Improve product quality, automate quality gates in CI, respond to MVP v1 customer feedback, and deliver a stable release with documented testing coverage |
| **Sprint Start** | 2026-06-16 |
| **Sprint End** | 2026-06-26 |
| **Total Story Points** | 34 |

### Sprint Scope Summary

- Addressed 3 of 5 customer feedback points from MVP v1 review
- Defined 4 quality requirements (ISO/IEC 25010)
- Linked automated quality requirement tests to all 4 QRs
- Added Bandit static security analysis as an additional QA check in CI
- Documented testing strategy, critical module coverage, and QRT evidence

---

## Links

| Artifact | Link |
|---|---|
| Product Backlog board | [_(link to GitHub/GitLab board)_](https://github.com/users/Aye-basota/projects/1) |
| Sprint Backlog board | [_(link to GitHub Projects / GitLab board)_](https://github.com/users/MuS0rKa/projects/1) |
| Assignment 4 Sprint milestone | [_(link to Sprint milestone)_](https://github.com/Aye-basota/AI-sales-manager/milestone/2) |
| Deployed product / run instructions | See [`LAUNCH_GUIDE.md`](../../LAUNCH_GUIDE.md) |
| `docs/roadmap.md` | [`docs/roadmap.md`](../../docs/roadmap.md) _(to be created)_ |
| `docs/definition-of-done.md` | [`docs/definition-of-done.md`](../../docs/definition-of-done.md) _(to be created)_ |
| `docs/quality-requirements.md` | [`docs/quality-requirements.md`](../../docs/quality-requirements.md) |
| `docs/quality-requirement-tests.md` | [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md) |
| `docs/testing.md` | [`docs/testing.md`](../../docs/testing.md) |
| `docs/user-acceptance-tests.md` | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md) _(to be created)_ |
| CI pipeline | _(link to CI pipeline)_ |
| Latest CI run | _(link to latest protected-branch CI run)_ |
| SemVer release | _(link to v0.4.0 release tag)_ |
| `CHANGELOG.md` | [`CHANGELOG.md`](../../CHANGELOG.md) _(to be created)_ |

---

## Part 2: Customer Feedback Response

### Feedback Response Table

The following feedback was collected from the customer during and after the MVP v1 Sprint Review.

| Feedback point | Resulting PBI or issue | Status | Response |
|---|---|---|---|
| Conversations feel robotic — the bot replies too quickly and uses structured lists. | Humanizer tuning PBI | Done | Increased thinking delay range (5–15 s), disabled list formatting in LLM prompt, added casual filler phrases. |
| Hard to tell at a glance which leads are warm or hot — the Admin Bot shows all dialogs in a flat list. | `/hotleads` command improvement PBI | Done | Added `/hotleads` command to Admin Bot that filters and lists only hot leads with last message preview. |
| The system sent a message to a lead at 02:00 — working hours filter did not apply correctly. | Timezone bug fix PBI | Done | Fixed timezone-aware working hours check in `scheduler.py` — was comparing naive datetime to aware datetime. Test added in `tests/test_timezone.py`. |
| Want to be able to export the contact list with current statuses to Excel. | Export feature PBI | Not planned for this Sprint | Deferred — data export is a P2 roadmap item. The priority for this Sprint was quality and automation. Backlog issue created. |
| The campaign progress counter shows "10/5 processed" which is confusing. | Processed contacts counter bug PBI | Not planned for this Sprint | Deferred — counter increments per message, not per unique contact. Known bug documented in `reports/week4/reflection.md`. Fix scheduled for Sprint 5. |

---

## Part 7: Testing and QA Summary

### Quality Model

We use **ISO/IEC 25010** as the quality model. The four quality requirements defined for Assignment 4 cover the following sub-characteristics:

| QR ID | Sub-characteristic | Category |
|---|---|---|
| QR-01 | Confidentiality | Security |
| QR-02 | Fault Tolerance | Reliability |
| QR-03 | Time Behaviour | Performance Efficiency |
| QR-04 | User Error Protection | Usability |

See [`docs/quality-requirements.md`](../../docs/quality-requirements.md) for full scenario definitions.

### Testing Status Summary

| Module | Type | Coverage | Status |
|---|---|---|---|
| `app/core/state_machine.py` | Unit | ~100% | ✅ |
| `app/llm/engine.py` | Unit | ~99% | ✅ |
| `app/llm/guardrails.py` | Unit | ~98% | ✅ |
| `app/services/notification_service.py` | Unit/Integration | ~96% | ✅ |
| `app/core/scheduler.py` | Integration | ~80% | ✅ |
| `app/bots/inbound_listener.py` | Integration | ~75% | ✅ |
| `app/services/conversation_service.py` | Integration | ~70% | ✅ |
| `app/core/humanizer.py` | Unit | ~68% | ✅ |
| **Global** | — | **~77%** | ✅ |

All critical modules exceed the required 30% line coverage threshold.

### Unit Tests

- [`tests/test_core_state_machine.py`](../../tests/test_core_state_machine.py)
- [`tests/test_llm_guardrails.py`](../../tests/test_llm_guardrails.py)
- [`tests/test_core_humanizer.py`](../../tests/test_core_humanizer.py)
- [`tests/test_llm_engine.py`](../../tests/test_llm_engine.py)
- [`tests/test_core_account_manager.py`](../../tests/test_core_account_manager.py)
- [`tests/test_db_redis.py`](../../tests/test_db_redis.py)

### Integration Tests

- [`tests/test_core_scheduler.py`](../../tests/test_core_scheduler.py)
- [`tests/test_bots_inbound_listener.py`](../../tests/test_bots_inbound_listener.py)
- [`tests/test_services_conversation_service.py`](../../tests/test_services_conversation_service.py)
- [`tests/test_services_contact_import.py`](../../tests/test_services_contact_import.py)

### Automated Quality Requirement Tests

- [`tests/test_llm_guardrails.py`](../../tests/test_llm_guardrails.py) — QR-01, QR-04
- [`tests/test_core_state_machine.py`](../../tests/test_core_state_machine.py) — QR-02
- [`tests/test_core_scheduler.py`](../../tests/test_core_scheduler.py) — QR-03

See [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md) for full QRT documentation.

### Additional QA Check: Bandit Static Security Analysis

**Options considered:** bandit (security linting), radon (complexity), safety (CVE scanning), pylint (quality).

**Selected:** `bandit -r app/ -ll` — runs after the test suite in CI.

**QA objective:** Detect Python security anti-patterns (hardcoded secrets, unsafe `eval()`, insecure subprocess calls) before they reach the main branch.

**Why this matters:** The system stores and transmits Telegram session strings. A hardcoded credential or unsafe string evaluation in the LLM processing path could expose accounts or allow code injection.

**Where it runs:** CI pipeline, separate `bandit` job after `pytest`.

**Limitations:** Static analysis only — does not catch runtime injection via LLM output. Reviewed and intentional subprocess calls are suppressed with `# nosec`.

CI pipeline screenshot: _(add `reports/week4/images/ci-run.png`)_
Coverage report screenshot: _(add `reports/week4/images/coverage-report.png`)_
Bandit result screenshot: _(add `reports/week4/images/bandit-result.png`)_

### Quality Gates Continuity

The tests, CI checks, QRTs, and coverage thresholds defined in Assignment 4 are maintained project assets. All later PRs/MRs must:
- Pass `pytest tests/` with no regressions.
- Pass `bandit -r app/ -ll` with no new medium/high severity issues.
- Maintain ≥ 30% line coverage on each critical module.
- Keep all QRT files (`test_llm_guardrails.py`, `test_core_state_machine.py`, `test_core_scheduler.py`) green.

These gates may only be changed by an explicit team decision with a documented reason in a PR description.

---

## Part 15: Public Sanitized Demo Video

**Status:** To be recorded before submission.

**Requirements:**
- Duration: < 2 minutes
- Content: demonstrate campaign creation, contact import, message sending simulation, hot lead alert
- Data: use sanitized demo data only (no real customer names, phone numbers, or Telegram IDs)
- Format: screen recording with voice-over or captions

**Link:** _(add public video link here after recording — YouTube unlisted or similar)_

Link this video from the SemVer release mapped to the Assignment 4 Sprint increment (v0.4.0).

---

## UAT Results Summary

| Scenario | Result | Notes |
|---|---|---|
| UAT-01: Import CSV contacts and launch campaign | Pass | Customer imported 15 test contacts successfully |
| UAT-02: AI bot sends initial message and follow-up | Pass | Messages arrived from real account; humanizer delays worked |
| UAT-03: Operator receives hot lead alert via Admin Bot | Pass | Alert arrived within 5 seconds of positive reply |

Most important feedback from UAT session:
- Customer confirmed the humanizer delays make conversations feel natural.
- Customer requested an easier way to view all open conversations — added to backlog.

Resulting PBIs: conversation list command improvement (backlog), export feature (backlog).

---

## Contribution Traceability

| Team Member | Issues | PRs/MRs | Review | Testing | Quality/Docs |
|---|---|---|---|---|---|
| _(Member 1)_ | _(links)_ | _(links)_ | _(links)_ | Scheduler, timezone tests | `docs/testing.md` |
| _(Member 2)_ | _(links)_ | _(links)_ | _(links)_ | Guardrails, state machine tests | `docs/quality-requirements.md`, QRTs |
| _(Member 3)_ | _(links)_ | _(links)_ | _(links)_ | Humanizer tuning, UAT | Feedback PBIs, reflection |

---

## Current Product Status

The core outbound and inbound automation pipeline is fully functional. Three of five customer feedback points addressed. Automated quality gates in CI. Known bugs documented (race condition, inbound flood bypass, processed_contacts metric) with fixes planned for Sprint 5.

## Next Steps

1. Fix race condition and inbound flood bypass (Sprint 5, P1).
2. Add conversation list command to Admin Bot.
3. Add API authentication layer.
4. Expand UAT scenarios to cover inbound reply → hot-lead alert flow.
5. Implement export feature (Excel, P2).

---

## Report Files

- [reflection.md](reflection.md)
- [retrospective.md](retrospective.md) _(to be written)_
- [customer-review-summary.md](customer-review-summary.md) _(to be written)_
- [llm-report.md](llm-report.md) _(to be written)_
