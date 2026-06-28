# Week 4 — Assignment 4 Sprint Report

## 1. Project

**Project name:** AI Sales Manager  
**Short description:** Autonomous B2B outbound sales assistant using real Telegram accounts and LLM-driven dialogue to generate qualified meetings.

---

## 2. Backlog and Sprint Planning

> Parts 1 and 2 are maintained by the team on GitHub. The links below are placeholders until the team finalises the boards.

- [Product Backlog board](https://github.com/Aye-basota/AI-sales-manager/projects) *(update link)*
- [Sprint Backlog board](https://github.com/Aye-basota/AI-sales-manager/projects) *(update link)*
- [Assignment 4 Sprint milestone](https://github.com/Aye-basota/AI-sales-manager/milestones) *(update link)*

### Sprint Goal
Deliver a reliable Assignment 4 Sprint increment by fixing known analytics/account bugs, adding demo seed data, automating quality requirement tests, and gating quality through CI.

### Sprint dates
2026-06-25 – 2026-07-09

### Scope summary
- Fix P1.3: analytics updates only for running campaigns.
- Fix P2: `processed_contacts` counts unique contacts, not messages.
- Fix `assigned_account_id` eligibility check with fallback.
- Add `scripts/seed_demo_data.py` for customer demos.
- Define and automate three Quality Requirement Tests (QRTs).
- Add `bandit` security scan to CI.
- Configure coverage reporting and artifacts in CI.
- Prepare SemVer release `v0.2.0`.

### Total Sprint size
To be filled by the team (Story Points).

---

## 3. Delivered Product Changes

- Health endpoint reports `degraded` when the scheduler is not running.
- Inbound analytics no longer count replies for paused/closed campaigns.
- `processed_contacts` now counts unique contacts.
- Assigned account selection validates status/session/cooldown and falls back.
- API returns HTTP 400 Bad Request for invalid request payloads.
- Demo seed data script available.

---

## 4. Deployment and Run Instructions

- **Local:** `docker-compose up -d --build` then `docker-compose exec api alembic upgrade head`.
- **Public access via localtunnel:** see [`LAUNCH_GUIDE.md`](../../LAUNCH_GUIDE.md).
- **Deployed product URL:** *(add localtunnel URL when running)*

---

## 5. Customer Feedback Response

| Feedback point | Resulting PBI or issue | Status | Response |
|---|---|---|---|
| Customer approved MVP v1; no specific changes requested. | — | Addressed | Increment focused on reliability, quality automation, and demo readiness. |
| Demo showed empty companies view. | Seed demo data | Done | Added `scripts/seed_demo_data.py` to populate analytics and contacts for demos. |

### Feedback not addressed
No outstanding feedback was left unaddressed from the Week 3 review.

---

## 6. Documentation Links

- [`docs/roadmap.md`](../../docs/roadmap.md)
- [`docs/definition-of-done.md`](../../docs/definition-of-done.md) *(team should update for QRTs/CI gates)*
- [`docs/quality-requirements.md`](../../docs/quality-requirements.md)
- [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md)
- [`docs/testing.md`](../../docs/testing.md)
- [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md) *(team should update/verify)*

---

## 7. Quality Model

Quality requirements use three different ISO/IEC 25010 sub-characteristics:
- **Time behaviour** (QR-001)
- **Availability** (QR-002)
- **Fault tolerance** (QR-003)

See [`docs/quality-requirements.md`](../../docs/quality-requirements.md) for details.

---

## 8. Testing Status

- **Total tests:** 430+
- **Coverage:** see latest CI artifact.
- **Critical module coverage:** all critical modules meet or exceed 30%.

### Links
- Unit tests: `tests/test_*.py`
- Integration tests: `tests/test_api_*.py`, `tests/test_e2e.py`
- Automated QRTs: [`tests/quality_requirement_tests/`](../../tests/quality_requirement_tests/)

---

## 9. CI and QA

- [CI pipeline](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml)
- [Latest protected-default-branch CI run](https://github.com/Aye-basota/AI-sales-manager/actions) *(select `main` branch)*
- Additional QA check: **bandit** security static analysis.

### Screenshots
Place screenshots in `reports/week4/images/`:
- `sprint-milestone.png`
- `ci-latest-run.png`
- `branch-protection.png`
- `coverage-report.png`
- `bandit-result.png`
- `semver-release.png`
- `reviewed-pr.png`

---

## 10. Release

- [SemVer release v0.2.0](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.2.0) *(created after push)*
- [`CHANGELOG.md`](../../CHANGELOG.md)

---

## 11. Demo Video

- [Public sanitized demo video](https://example.com/demo-video) *(team should upload and update)*

---

## 12. UAT and Customer Review

- **UAT results summary:** *(team should update after customer UAT)*
- [`customer-review-summary.md`](customer-review-summary.md)
- [`customer-review-transcript.md`](customer-review-transcript.md) *(only if publication permitted)*
- [`customer-review-notes.md`](customer-review-notes.md) *(if recording refused)*

---

## 13. Team Reflection

- [`reflection.md`](reflection.md) *(team should update)*
- [`retrospective.md`](retrospective.md) — Sprint 2 retrospective (Assignment 4 Part 12)
- [`llm-report.md`](llm-report.md) — AI/LLM usage disclosure (Assignment 4 Part 16)

---

## 14. Current Product Status and Next Steps

**Current status:** MVP v1 delivered and approved. Assignment 4 increment focuses on quality, automation, and reliability.

**Next steps:**
- Team to push `main` and `v0.2.0` tag to GitHub.
- Run localtunnel or deploy to a server for TA/customer access.
- Conduct UAT and Sprint Review with the customer.
- Update Week 4 report with screenshots, demo video, and UAT results.

---

## 15. Contribution Traceability

| Team member | Issues | PRs/MRs | Reviews | Testing | QA / Automation | Documentation |
|---|---|---|---|---|---|---|
| *(fill in)* | | | | | | |

---

*This report is a living document. Sections marked with placeholders must be completed by the team before final submission.*
