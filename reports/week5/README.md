# Week 5 — Assignment 5 Sprint Report

## 1. Project

**Project name:** AI Sales Manager  
**Short description:** Autonomous B2B outbound sales assistant using real Telegram accounts and LLM-driven dialogue to generate qualified meetings.

---

## 2. Backlog and Sprint Planning

- [Product Backlog board](https://github.com/users/Aye-basota/projects/1/views/1)
- [Sprint Backlog board](https://github.com/Aye-basota/AI-sales-manager/projects) *(filter by Sprint 3 milestone after creation)*
- [Sprint 3 milestone](https://github.com/Aye-basota/AI-sales-manager/milestones) *(create Sprint 3 milestone if it does not exist)*

### Sprint Goal

Deliver the `MVP v2` increment for Assignment 5 by implementing the selected Sprint scope, responding to customer feedback, and extending testing, QA, and deployment evidence.

### Sprint dates

2026-06-30 – 2026-07-06

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

Also included:
- Update Definition of Done, testing, and quality documentation.
- Deploy the current increment and create SemVer release `v0.3.0`.
- Publish maintained documentation as a hosted site.

### Total Sprint size

*(to be filled by Product Owner in the Sprint Backlog board)*

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
- **Tests:** 459 automated tests, `app/` coverage ≥ 80%; new tests for funnel API, automation rate, prompt config, and conversation escalation.

---

## 4. Deployment and Run Instructions

- **Local:** `docker-compose up -d --build` then `docker-compose exec api alembic upgrade head`.
- **Public access via localtunnel:** see [`LAUNCH_GUIDE.md`](../../LAUNCH_GUIDE.md).
- **Deployed product URL:** *(add URL when running)*
- **Access instructions / test credentials:** *(add if needed)*

---

## 5. Customer Feedback Response

| Feedback point | Resulting PBI or issue | Status | Response |
|---|---|---|---|
| First messages felt too salesy / mass-mailing | US-017, US-018 | Done | Reworked default funnel to trust-building stages and external prompt config for easy tuning |
| Need to upload funnel definitions from files/markdown | TECH-04, TECH-05 | Done | Added `POST /api/funnels/preview` and `POST /api/funnels/upload` with JSON/text parsers |
| Want visibility into how many dialogs are fully automated | TECH-06 | Done | Added `was_escalated` flag and `GET /analytics/automation-rate` |
| Hard to tell if production service is healthy after deploy | TECH-12 | Done | Added structured logging, `/health`, Docker health checks, and restart policies |

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
- [`docs/architecture/README.md`](../../docs/architecture/README.md)
- ADR directory: [`docs/architecture/adr/`](../../docs/architecture/adr/)

---

## 7. Quality Model

Quality requirements use ISO/IEC 25010 sub-characteristics:

- **Time behaviour** ([QR-001](../../docs/quality-requirements.md#qr-001-health-endpoint-response-time))
- **Availability** ([QR-002](../../docs/quality-requirements.md#qr-002-core-system-availability-proxy))
- **Fault tolerance** ([QR-003](../../docs/quality-requirements.md#qr-003-api-fault-tolerance-on-invalid-input))
- *(add new QR-00X for MVP v2 when defined)*

See [`docs/quality-requirements.md`](../../docs/quality-requirements.md) for details.

---

## 8. Testing Status

- **Total tests:** 459
- **Coverage:** `app/` ≥ 80% (latest local run)
- **Critical module coverage:** all critical modules meet or exceed 30%.
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
- [Latest protected-default-branch CI run](https://github.com/Aye-basota/AI-sales-manager/actions) *(select `main` branch)*
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

- [SemVer release v0.3.0](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.3.0) *(create after push)*
- [`CHANGELOG.md`](../../CHANGELOG.md)

---

## 11. Demo Video

- [Public sanitized demo video](https://example.com/demo-video) *(team should upload and update)*

---

## 12. UAT and Customer Review

- **UAT results summary:** *(team should update after customer UAT)*
- [`reports/week5/sprint-review-summary.md`](sprint-review-summary.md)
- [`reports/week5/sprint-review-transcript.md`](sprint-review-transcript.md) *(only if publication permitted)*
- [`reports/week5/sprint-review-notes.md`](sprint-review-notes.md) *(if recording refused)*

---

## 13. Architecture Summary

MVP v2 keeps the existing async FastAPI + PostgreSQL + Redis architecture and adds three new bounded capabilities:

1. **Prompt configuration layer** (`app/config/prompts/`) isolates LLM prompts from business logic, enabling versioned prompt updates without redeploying code.
2. **Funnel management layer** (`app/services/funnel_parser.py`, `app/api/funnels.py`, `app/models/funnel.py`) lets operators upload and preview sales funnels in JSON or plain text, validated before persistence.
3. **Observability layer** (`app/logging_config.py`, `/health`, Docker health checks) exposes structured logs and a lightweight health endpoint for production monitoring.

The lead-nurturing funnel is implemented in `app/core/funnel.py` and consumed by `app/llm/prompts.py`, so stage-specific instructions flow naturally into LLM prompts while preserving backward compatibility for legacy stage names.

Automation-rate tracking uses the existing `conversations` table plus a `was_escalated` boolean; any operator-driven status change marks the dialog as escalated, and `GET /analytics/automation-rate` returns the AI-handled ratio.

- Static view: [`docs/architecture/static-view/`](../../docs/architecture/static-view/)
- Dynamic view: [`docs/architecture/dynamic-view/`](../../docs/architecture/dynamic-view/)
- Deployment view: [`docs/architecture/deployment-view/`](../../docs/architecture/deployment-view/)

Quality requirements are traced to tests in [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md).

---

## 14. Team Reflection

- [`reflection.md`](reflection.md) *(team should update)*
- [`retrospective.md`](retrospective.md) *(team should update)*
- [`llm-report.md`](llm-report.md) *(team should update)*

---

## 15. Current Product Status and Next Steps

**Current status:** `MVP v2` delivered for Assignment 5.

**Next steps:**

- Merge the feature branch into `main` and push.
- Create GitHub release `v0.3.0` from the merged `main`.
- Enable GitHub Pages source `gh-pages` after the docs workflow runs once.
- Deploy to the target VPS (`docker-compose up -d --build`, `alembic upgrade head`).
- Conduct Sprint Review and UAT with the customer.
- Record public sanitized demo video and update section 11.
- Fill remaining placeholders (Sprint size, screenshots, UAT results, team reflection).
- Prepare Assignment 5 Moodle PDF submission.

---

## 16. Contribution Traceability

| Team member | Issues | PRs/MRs | Reviews | Testing | QA / Automation | Documentation |
|---|---|---|---|---|---|---|
| *(fill in)* | | | | | | |

---

*This report is a living document. Sections marked with placeholders must be completed by the team before final submission.*
