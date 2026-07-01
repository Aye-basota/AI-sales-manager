# Product Roadmap

## Product Goal

Build an autonomous B2B outbound sales assistant that uses real Telegram accounts and LLM-driven dialogue to generate qualified meetings with minimal human intervention.

---

## Completed Sprints

### Sprint 1 — MVP v1

**Goal:** Deliver a working sales funnel for automated Telegram outreach, from first contact to meeting booking.

**Dates:** 2026-06-09 – 2026-06-20

**Key deliverables:**

- Configurable 4-stage sales funnel (hook → qualification → value → CTA).
- Funnel-aware LLM prompt generation and stage tracking in `Conversation`.
- Admin bot script creation with `first_message_goal` selection.
- Analytics dashboard for replies, qualified leads, and meetings booked.
- Multi-provider LLM support (OpenRouter + DashScope).
- SemVer release **v0.1.0**.

### Sprint 2 — Assignment 4 (Quality & Reliability)

**Goal:** Deliver a reliable Sprint increment by fixing known analytics and account bugs, automating quality requirement tests, and gating quality through CI — while improving demo readiness for customer review.

**Dates:** 2026-06-25 – 2026-06-28 (increment released as **v0.2.0**)

**Key deliverables:**

- Bug fixes: analytics for running campaigns only, unique `processed_contacts` count, assigned-account eligibility with fallback.
- Health endpoint reports `degraded` when the scheduler is not running; invalid JSON returns HTTP 400.
- Three quality requirements (QR-001–QR-003) with automated QRTs in CI.
- CI pipeline: lint (ruff), tests with coverage artifacts, bandit security scan.
- Demo seed script (`scripts/seed_demo_data.py`) and localtunnel deployment path.
- Updated Definition of Done, testing strategy, and Week 4 report structure.
- SemVer release **v0.2.0** mapped to [Sprint 2 milestone](https://github.com/Aye-basota/AI-sales-manager/milestone/2).

**Deferred to later sprints:** full campaign-launch workflow (US-011, US-012, TECH-07–TECH-10) — selected in Sprint 2 planning but not completed; quality and reliability work took priority for Assignment 4.

---

。## Current Sprint

### Sprint 3 — MVP v2 (Lead Nurturing, Configurability, and Production Readiness)

**Goal:** Deliver the `MVP v2` increment by making the dialogue more nurturing and configurable, adding funnel management APIs, and improving production observability and security.

**Dates:** 2026-06-30 – 2026-07-06

**Selected PBIs (from Product Backlog):**

| ID | Title | Priority |
|---|---|---|
| US-017 | Improve prompts for lead nurturing | Must Have |
| US-018 | Natural multi-stage conversation flow | Must Have |
| TECH-04 | Funnel upload API | Must Have |
| TECH-05 | Funnel preview API | Must Have |
| TECH-06 | AI-automation rate tracking | Should Have |
| TECH-13 | Prompt configuration and versioning | Should Have |
| TECH-12 | Production monitoring | Should Have |

**Sprint focus:**

- Rework default funnel to trust-building stages and externalize prompt templates.
- Allow operators to preview and upload funnel definitions via API.
- Track AI-automation rate and expose it through analytics.
- Add health checks, structured logging, and container restart policies for production.
- Resolve known dependency vulnerabilities and extend CI with `pip-audit` and `lychee`.
- SemVer release **v0.3.0** mapped to [Sprint 3 milestone](https://github.com/Aye-basota/AI-sales-manager/milestones).

---

## Next Sprint

### Sprint 4 — Operator Control and Campaign Launch Hardening

**Goal:** Complete the campaign-launch workflow for MVP validation and give operators more control over live conversations.

**Planned PBIs:**

- US-011: Import Contact Base from CSV
- US-012: Launch Outreach Campaign to Contact Base
- US-016: Campaign Launch Readiness Check
- TECH-07–TECH-10: CSV import and campaign launch internals
- US-09: Manual Dialog Takeover
- US-013: Monitor Active Dialogs in Real Time

**Planned outcomes:**

- Sales directors can import contacts and launch end-to-end outreach campaigns.
- Operators can monitor and optionally take over active dialogs.
- Persistent staging deployment for customer demos and UAT.

---

## Ongoing Quality and Automation (maintained from Assignment 4 and extended in Assignment 5)

These gates apply to **all future sprints** unless explicitly superseded:

| Asset | Location | Expectation |
|---|---|---|
| Quality requirements | `docs/quality-requirements.md` | New features must not regress QR-001–QR-008 scenarios |
| Automated QRTs | `tests/quality_requirement_tests/` + `tests/test_api_*.py` | Run on every CI build |
| Definition of Done | `docs/definition-of-done.md` | PBIs marked Done only when CI, tests, review, changelog, and release criteria are met |
| Testing strategy | `docs/testing.md` | Critical modules maintain ≥ 30% line coverage |
| CI pipeline | `.github/workflows/ci.yml` | Tests, coverage, bandit, pip-audit, flake8 must pass on `main` |
| Link checker | `.github/workflows/links.yml` | No broken links in documentation |
| UAT scenarios | `docs/user-acceptance-tests.md` | Re-executed after major increments |

---

## Future Directions

- Voice message support
- Image and media processing
- CRM integrations (HubSpot, Pipedrive)
- Calendar integrations (Google Calendar, Calendly)
- Advanced campaign analytics and real-time dashboards
- A/B testing for outreach campaigns
- Human-like message pacing improvements (typing indicators, chunk splitting)
