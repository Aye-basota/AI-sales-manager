# Week 5 — Assignment 5 Sprint Report

## 1. Project

**Project name:** AI Sales Manager  
**Short description:** Autonomous B2B outbound sales assistant using real Telegram accounts and LLM-driven dialogue to generate qualified meetings.

---

## 2. Backlog and Sprint Planning

- [Product Backlog board](https://github.com/users/Aye-basota/projects/1/views/1)
- [Sprint Backlog board](https://github.com/users/Aye-basota/projects/3/views/1?layout=board)
- [Sprint 3 milestone](https://github.com/Aye-basota/AI-sales-manager/milestone/3)

### Sprint Goal

Deliver MVP v2 by deploying the application to a production VPS for reliable 24/7 availability and enhancing the AI assistant with improved prompts, a more natural conversational flow, and a structured lead nurturing process that builds trust before guiding users through the sales funnel.

### Sprint dates

2026-06-29 – 2026-07-04

### Scope summary

Selected Sprint 3 PBIs from the GitHub backlog:

| Issue | Type | Title |
|---|---|---|
| [#51](https://github.com/Aye-basota/AI-sales-manager/issues/51) | US | US-017 — Improve prompts for lead nurturing |
| [#52](https://github.com/Aye-basota/AI-sales-manager/issues/52) | US | US-018 — Natural multi-stage conversation flow |
| [#24](https://github.com/Aye-basota/AI-sales-manager/issues/24) | Tech | TECH-04 — Funnel upload API |
| [#25](https://github.com/Aye-basota/AI-sales-manager/issues/25) | Tech | TECH-05 — Funnel preview API |
| [#26](https://github.com/Aye-basota/AI-sales-manager/issues/26) | Tech | TECH-06 — AI-automation rate tracking |
| [#55](https://github.com/Aye-basota/AI-sales-manager/issues/55) | Tech | TECH-13 — Prompt configuration and versioning |
| [#54](https://github.com/Aye-basota/AI-sales-manager/issues/54) | Tech | TECH-12 — Production monitoring |
| [#53](https://github.com/Aye-basota/AI-sales-manager/issues/53) | Tech | TECH-11 — Deploy Application to Production VPS |

Also included:
- Update Definition of Done, testing, and quality documentation.
- Deploy the current increment and create SemVer release `v0.3.0`.
- Publish maintained documentation as a hosted site.

### Total Sprint size

35 Story Points (23 SP user stories + 12 SP technical tasks).

---

## 3. Delivered Product Changes

- **TECH-13 — Prompt versioning:** prompts moved to `app/config/prompts/v1.json`; versioned config loader with safe template formatting.
- **US-017 — Lead-nurturing prompts:** default funnel stages reworked to `trust → engagement → qualification → value → cta` with stage-specific goals, instructions, and length limits.
- **US-018 — Natural multi-stage flow:** conversation progression uses the new nurturing stages; legacy stage aliases (`hook` → `trust`) keep old conversations compatible.
- **TECH-04 / TECH-05 — Funnel upload/preview API:** `POST /api/funnels/preview` and `POST /api/funnels/upload` support JSON and plain-text funnel definitions, validation, duplicate-stage checks, and overwrite guard for running campaigns.
- **TECH-06 — AI-automation rate:** `Conversation.was_escalated` flag set on operator status changes; new `GET /analytics/automation-rate` endpoint reports AI-handled vs escalated dialogs.
- **TECH-12 — Production monitoring:** centralized logging (`app/logging_config.py`), `LOG_LEVEL` env variable, Docker Compose health check for the API container, and `restart: unless-stopped` for all services.
- **Docs site:** MkDocs Material site under `docs/`, published via `.github/workflows/docs.yml` to GitHub Pages.
- **QA pipeline extensions:** added `pip-audit` and `lychee` jobs; updated dependencies to resolve known vulnerabilities (FastAPI 0.138.2, Starlette 1.3.1, Pydantic 2.13.4).
- **Tests:** 459 automated tests, `app/` coverage ~81%; new tests for funnel API, automation rate, prompt config, and conversation escalation.
  - Local verification: `pytest tests/` — 459 passed; `bandit -r app/ -ll` — no issues; `pip-audit` — no known vulnerabilities; `flake8` — no issues.

---

## 4. Deployment and Run Instructions

- **Local:** `docker-compose up -d --build` then `docker-compose exec api alembic upgrade head`.
- **Public access via localtunnel:** see [`LAUNCH_GUIDE.md`](../../LAUNCH_GUIDE.md).
- **Deployed product URL:** https://witty-cases-trade.loca.lt (localtunnel; active while the host machine and tunnel are running)
- **Access instructions / test credentials:** No special credentials required. Health check: `GET /health`. API docs: `/docs`.

---

## 5. Customer Feedback Response

| Feedback point | Resulting PBI or issue | Status | Response |
|---|---|---|---|
| AI responses felt too sales-oriented and unnatural | [#51 US-017](https://github.com/Aye-basota/AI-sales-manager/issues/51) | Done | Improved prompt structure and externalized prompt config for easy tuning |
| Conversation does not gradually build trust before selling | [#52 US-018](https://github.com/Aye-basota/AI-sales-manager/issues/52) | Done | Introduced structured multi-stage dialogue (trust → engagement → qualification → value → CTA) |
| No production deployment / system not always available | [#53 TECH-11](https://github.com/Aye-basota/AI-sales-manager/issues/53) | Done | VPS deployment via Docker Compose with restart policies |
| No system monitoring or reliability guarantees | [#54 TECH-12](https://github.com/Aye-basota/AI-sales-manager/issues/54) | Done | Added `/health`, structured logging, Docker health checks, and auto-restart |
| Prompt quality is inconsistent across conversations | [#55 TECH-13](https://github.com/Aye-basota/AI-sales-manager/issues/55) | Done | Centralized prompt management and versioning in `app/config/prompts/v1.json` |
| Need to upload funnel definitions from files/markdown | [#24 TECH-04](https://github.com/Aye-basota/AI-sales-manager/issues/24) / [#25 TECH-05](https://github.com/Aye-basota/AI-sales-manager/issues/25) | Done | Added `POST /api/funnels/preview` and `POST /api/funnels/upload` with JSON/text parsers |
| Want visibility into how many dialogs are fully automated | [#26 TECH-06](https://github.com/Aye-basota/AI-sales-manager/issues/26) | Done | Added `was_escalated` flag and `GET /analytics/automation-rate` |
| Advanced analytics dashboard not available | — | Deferred | Deferred due to MVP v2 focus on production stability and AI conversation quality |
| CRM integrations not implemented | — | Deferred | Out of scope for MVP v2; planned for future iterations |

### Feedback not addressed

Deferred to future sprints:
- Manual operator takeover of a live conversation (`is_paused_by_operator`).
- Calendar integration when meeting intent is detected.

---

## 6. Documentation Links

- [`docs/roadmap.md`](../../docs/roadmap.md)
- [`docs/definition-of-done.md`](../../docs/definition-of-done.md)
- [`docs/testing.md`](../../docs/testing.md)
- [`docs/quality-requirements.md`](../../docs/quality-requirements.md)
- [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md)
- [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md)
- [`docs/development-process.md`](../../docs/development-process.md)
- [`docs/interface.md`](../../docs/interface.md)
- [`docs/architecture/README.md`](../../docs/architecture/README.md)
- Static view: [`docs/architecture/static-view/component-diagram.puml`](../../docs/architecture/static-view/component-diagram.puml)
- Dynamic view: [`docs/architecture/dynamic-view/inbound-reply-sequence.puml`](../../docs/architecture/dynamic-view/inbound-reply-sequence.puml)
- Deployment view: [`docs/architecture/deployment-view/deployment-diagram.puml`](../../docs/architecture/deployment-view/deployment-diagram.puml)
- ADR directory: [`docs/architecture/adr/`](../../docs/architecture/adr/)
- Hosted documentation site: [`https://aye-basota.github.io/AI-sales-manager/`](https://aye-basota.github.io/AI-sales-manager/)

---

## 7. Quality Model

Quality requirements use ISO/IEC 25010 quality sub-characteristics:

- **Security — Confidentiality** ([QR-01](../../docs/quality-requirements.md#qr-01))
- **Reliability — Fault Tolerance** ([QR-02](../../docs/quality-requirements.md#qr-02))
- **Performance Efficiency — Time Behaviour** ([QR-03](../../docs/quality-requirements.md#qr-03))
- **Usability — User Error Protection** ([QR-04](../../docs/quality-requirements.md#qr-04))
- **Maintainability — Modifiability** ([QR-05](../../docs/quality-requirements.md#qr-05))
- **Functional Suitability — Functional Correctness** ([QR-06](../../docs/quality-requirements.md#qr-06))
- **Reliability — Availability / Maintainability** ([QR-07](../../docs/quality-requirements.md#qr-07))
- **Functional Suitability — Accuracy** ([QR-08](../../docs/quality-requirements.md#qr-08))

See [`docs/quality-requirements.md`](../../docs/quality-requirements.md) for details.

---

## 8. Testing Status

- **Total tests:** 459
- **Coverage:** `app/` ~81% (latest local run)
- **Critical module coverage:** all critical modules meet or exceed 30%.
  | Module | Coverage |
  |---|---|
  | `app/core/state_machine.py` | 100% |
  | `app/api/analytics.py` | 100% |
  | `app/api/conversations.py` | 100% |
  | `app/api/health.py` | 100% |
  | `app/llm/engine.py` | 94% |
  | `app/llm/guardrails.py` | 90% |
  | `app/services/notification_service.py` | 94% |
  | `app/core/scheduler.py` | 80% |
  | `app/bots/inbound_listener.py` | 79% |
  | `app/services/conversation_service.py` | 86% |
  | `app/core/humanizer.py` | 92% |
  | `app/core/funnel.py` | 88% |
- **New tests added this Sprint:**
  - `tests/test_api_funnels.py` — funnel preview/upload API (TECH-04/05)
  - `tests/test_api_analytics.py` — automation-rate endpoint (TECH-06)
  - `tests/test_api_conversations.py` — escalation flag update (TECH-06)
  - Updated `tests/test_core_funnel.py` and `tests/test_llm_funnel_prompts.py` for lead-nurturing stages

### Links

- Unit tests: `tests/test_*.py`
- Integration tests: `tests/test_api_*.py`, `tests/test_e2e.py`
- Automated QRTs: [`tests/quality_requirement_tests/`](../../tests/quality_requirement_tests/)

---

## 9. CI and QA

- [CI pipeline](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml)
- [Link checker](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/links.yml)
- [Latest protected-default-branch CI run](https://github.com/Aye-basota/AI-sales-manager/actions?query=branch%3Amain)
- Additional QA checks: **bandit** security static analysis, **pip-audit** dependency vulnerability scan.

### Screenshots

Place screenshots in `reports/week5/images/`:

- `sprint-milestone.png`
- `board-or-project-workflow.png`
- `ci-latest-run.png`
- `semver-release.png`
- `reviewed-pr.png`
- `hosted-docs-site.png`
- `product-access.png` *(if relevant)*

---

## 10. Release

- [SemVer release v0.3.0](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.3.0) *(team-only: create from the `main` commit after merge)*
- [`CHANGELOG.md`](../../CHANGELOG.md)

---

## 11. Demo Video

- [Public sanitized demo video](https://drive.google.com/file/d/1fwjMV_nN-RU7BLEL8t7nbmfAnLhxXLFK/view?usp=sharing) 

---

## 12. **UAT and Customer Review:**
Sprint: 3 (MVP v2)
Session date: 2026-07-05
Executed with: Mark (customer)
Scenarios Passed
UAT 1 — 24/7 Production Availability via VPS Deployment: Confirmed working. The customer tested the bot with the local development environment (including Docker) fully shut down and received correct, timely responses.
UAT 2 — Natural Conversational Flow and Structured Lead Nurturing: Confirmed working. The bot now asks clarifying questions and guides the conversation toward booking instead of returning a flat price/answer.
Regression — Standard Q&A and Off-Topic Handling: Confirmed unaffected by the production migration.
Scenarios Failed / Needing Changes
None of the executed UAT scenarios failed.
What Still Needs to Be Fixed in the Product
The admin panel does not currently support returning to a previous step (e.g., after confirming a campaign launch) to edit or correct data such as uploaded contacts. This was raised as a usability gap by the customer.
Most Important Feedback Points Received
Overall satisfaction with the delivered increment: reliability (24/7 availability) and conversational quality (natural, consultative dialogue) were both explicitly confirmed as improvements over the previous version.
Primary improvement request: a more intuitive, editable admin panel workflow — specifically the ability to go back and correct data after a step (such as campaign launch) has already been confirmed.
Resulting PBIs / Issues
- [US-019: Improve Admin Panel Navigation — Allow Editing After Campaign Launch Step](https://github.com/Aye-basota/AI-sales-manager/issues/68) (#68), targeted for Sprint 4.
Related Artifacts
Full UAT scenarios and acceptance criteria: `docs/user-acceptance-tests.md`
Sprint Review summary: `reports/week5/sprint-review-summary.md`
Sprint Review / UAT transcript: `reports/week5/sprint-review-transcript.md`
> The private recording of this session is submitted separately via Moodle (accessible to instructors only), with Moodle-only timecodes indicating where the customer-executed UAT and Sprint Review discussion occur. It is not included in this public repository.
Related Artifacts
Full UAT scenarios and acceptance criteria: `docs/user-acceptance-tests.md`
Sprint Review summary: `reports/week5/sprint-review-summary.md`
Sprint Review / UAT transcript: `reports/week5/sprint-review-transcript.md`
> The private recording of this session is submitted separately via Moodle (accessible to instructors only), with Moodle-only timecodes indicating where the customer-executed UAT and Sprint Review discussion occur. It is not included in this public repository.
---

## 13. Architecture Summary

MVP v2 keeps the existing async FastAPI + PostgreSQL + Redis architecture and adds three new bounded capabilities:

1. **Prompt configuration layer** (`app/config/prompts/`) isolates LLM prompts from business logic, enabling versioned prompt updates without redeploying code.
2. **Funnel management layer** (`app/services/funnel_parser.py`, `app/api/funnels.py`, `app/models/funnel.py`) lets operators upload and preview sales funnels in JSON or plain text, validated before persistence.
3. **Observability layer** (`app/logging_config.py`, `/health`, Docker health checks) exposes structured logs and a lightweight health endpoint for production monitoring.

MVP v2 runs as a Docker Compose stack (FastAPI + Admin Bot + APScheduler + Pyrogram) with PostgreSQL and Redis. Architecture is documented with diagrams-as-code and linked ADRs:

- **Overview (static, dynamic, deployment views):** [`docs/architecture/README.md`](../../docs/architecture/README.md)
- **Component diagram source:** [`docs/architecture/static-view/component-diagram.puml`](../../docs/architecture/static-view/component-diagram.puml)
- **Sequence diagram source:** [`docs/architecture/dynamic-view/inbound-reply-sequence.puml`](../../docs/architecture/dynamic-view/inbound-reply-sequence.puml)
- **Deployment diagram source:** [`docs/architecture/deployment-view/deployment-diagram.puml`](../../docs/architecture/deployment-view/deployment-diagram.puml)
- **ADRs:** [`docs/architecture/adr/`](../../docs/architecture/adr/)

Quality requirements QR-01–QR-08 are traced to ADR-001–ADR-008 and verified by automated QRTs in CI. See [`docs/quality-requirements.md`](../../docs/quality-requirements.md) and [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md).

---

## 14. Team Reflection

- [`reflection.md`](reflection.md) *(team should update)*
- [`retrospective.md`](retrospective.md) — Sprint 3 retrospective (Part 10)
- [`llm-report.md`](llm-report.md) — LLM usage report (Part 14)

---

## 15. Current Product Status and Next Steps

**Current status:** `MVP v2` code, tests, QA gates, documentation, and changelog are complete. The branch is ready to merge into `main`.

**Next steps (team-only):**

1. Merge `assignment5-parts-6-7-11-prep` into `main` via PR + review.
2. Create GitHub release `v0.3.0` from the merged `main` commit.
3. Deploy the current increment and fill the public URL in section 4.
4. Record the public sanitized demo video (<2 min) and update section 11.
5. Add screenshots to `reports/week5/images/`.
6. Prepare the Assignment 5 Moodle PDF submission.

---

## 16. Contribution Traceability

| Team member | Issues | PRs/MRs | Reviews | Testing | QA / Automation | Documentation |
|---|---|---|---|---|---|---|
| *(team-only: one row per member with links to issues/PRs)* | | | | | | |

---

*This report is a living document. Sections marked as **team-only** must be completed by the team before final submission.*
