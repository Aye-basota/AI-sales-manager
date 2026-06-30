# Week 5 — Assignment 5 Sprint Report

## 1. Project

**Project name:** AI Sales Manager  
**Short description:** Autonomous B2B outbound sales assistant using real Telegram accounts and LLM-driven dialogue to generate qualified meetings.

---

## 2. Backlog and Sprint Planning

- [Product Backlog board](https://github.com/Aye-basota/AI-sales-manager/projects) *(update link)*
- [Sprint Backlog board](https://github.com/Aye-basota/AI-sales-manager/projects) *(update link)*
- [Sprint 3 milestone](https://github.com/Aye-basota/AI-sales-manager/milestones) *(update link)*

### Sprint Goal

Deliver MVP v2 by deploying the application to a production VPS for reliable 24/7 availability and enhancing the AI assistant with improved prompts, a more natural conversational flow, and a structured lead nurturing process that builds trust before guiding users through the sales funnel.

### Sprint dates

2026-07-06 – 2026-07-12 *(update if different)*

### Scope summary

- Implement selected `MVP v2` product changes.
- Address selected customer feedback from `MVP v1`.
- Extend automated tests and QRTs for new product areas.
- Update Definition of Done, testing, and quality documentation.
- Deploy the current increment and create SemVer release `v0.3.0`.
- Publish maintained documentation as a hosted site.

### Total Sprint size

*(fill in Story Points)*

---

## 3. Delivered Product Changes

- *(to be filled after Sprint implementation)*
- *(list user-visible features, bug fixes, architecture improvements)*

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
| *(to be filled)* | *(issue link)* | *(Done / Deferred)* | *(response)* |

### Feedback not addressed

*(explain any feedback points intentionally deferred)*

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

- **Total tests:** *(update after Sprint)*
- **Coverage:** see latest CI artifact.
- **Critical module coverage:** all critical modules meet or exceed 30%.

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

MVP v2 runs as a Docker Compose stack (FastAPI + Admin Bot + APScheduler + Pyrogram) with PostgreSQL and Redis. Architecture is documented with diagrams-as-code and linked ADRs:

- **Overview (static, dynamic, deployment views):** [`docs/architecture/README.md`](../../docs/architecture/README.md)
- **Component diagram source:** [`docs/architecture/static-view/component-diagram.puml`](../../docs/architecture/static-view/component-diagram.puml)
- **Sequence diagram source:** [`docs/architecture/dynamic-view/inbound-reply-sequence.puml`](../../docs/architecture/dynamic-view/inbound-reply-sequence.puml)
- **Deployment diagram source:** [`docs/architecture/deployment-view/deployment-diagram.puml`](../../docs/architecture/deployment-view/deployment-diagram.puml)
- **ADRs:** [`docs/architecture/adr/`](../../docs/architecture/adr/)

Quality requirements QR-01–QR-04 map to ADR-001–ADR-004 (guardrails, state machine, scheduler, anti-repetition) and are verified by QRTs in CI. See [`docs/quality-requirements.md`](../../docs/quality-requirements.md).

---

## 14. Team Reflection

- [`reflection.md`](reflection.md) *(team should update)*
- [`retrospective.md`](retrospective.md) — Sprint 3 retrospective (Part 10)
- [`llm-report.md`](llm-report.md) — LLM usage report (Part 14)

---

## 15. Current Product Status and Next Steps

**Current status:** `MVP v2` delivered for Assignment 5.

**Next steps:**

- Conduct Sprint Review and UAT with the customer.
- Record public sanitized demo video.
- Fill remaining placeholders in this report.
- Prepare Assignment 5 Moodle PDF submission.

---

## 16. Contribution Traceability

| Team member | Issues | PRs/MRs | Reviews | Testing | QA / Automation | Documentation |
|---|---|---|---|---|---|---|
| *(fill in)* | | | | | | |

---

*This report is a living document. Sections marked with placeholders must be completed by the team before final submission.*
