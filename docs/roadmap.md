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

## Current Sprint

### Sprint 3 — Operator Control and Campaign Launch

**Goal:** Complete the campaign-launch workflow for MVP validation and give operators more control over live conversations.

**Dates:** 2026-06-28 – 2026-07-12 (planned)

**Selected PBIs (from Product Backlog):**

| ID | Title | Priority |
|---|---|---|
| US-011 | Import Contact Base from CSV | Must Have (mvp-v1) |
| US-012 | Launch Outreach Campaign to Contact Base | Must Have (mvp-v1) |
| US-016 | Campaign Launch Readiness Check | Should Have |
| TECH-07 | CSV contact import — parsing, validation, and preview | Technical |
| TECH-08 | CSV contact import — persistence and duplicate handling | Technical |
| TECH-09 | Campaign scheduler with working-hours and anti-spam controls | Technical |
| TECH-10 | Campaign launch endpoint and contact-base assignment | Technical |
| US-09 | Manual Dialog Takeover | Could Have |
| US-013 | Monitor Active Dialogs in Real Time | Could Have |

**Sprint focus:**

- Finish CSV import and campaign launch so a sales director can run an end-to-end outreach campaign.
- Improve operator visibility (dialog monitoring, optional manual takeover).
- Provision a persistent staging deployment for customer demos and UAT.

---

## Next Sprint

### Sprint 4 — Analytics and Management Tooling

**Goal:** Increase visibility into campaign performance and streamline day-to-day management through the Admin Bot.

**Planned PBIs:**

- US-015: Campaign Analytics and Conversion Dashboard
- US-010: Telegram Admin Bot for Management (complete remaining UX)
- US-014: Lead Qualification Status Management

**Planned outcomes:**

- Conversion metrics visible per campaign and funnel stage.
- Improved Admin Bot menus, command hints, and entity navigation.
- Clear lead qualification states for operator handover.

---

## Ongoing Quality and Automation (maintained from Assignment 4)

These gates apply to **all future sprints** unless explicitly superseded:

| Asset | Location | Expectation |
|---|---|---|
| Quality requirements | `docs/quality-requirements.md` | New features must not regress QR-001–QR-003 scenarios |
| Automated QRTs | `tests/quality_requirement_tests/` | Run on every CI build |
| Definition of Done | `docs/definition-of-done.md` | PBIs marked Done only when CI, tests, review, and changelog criteria are met |
| Testing strategy | `docs/testing.md` | Critical modules maintain ≥ 30% line coverage |
| CI pipeline | `.github/workflows/ci.yml` | Lint, tests, coverage, bandit must pass on `main` |
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
