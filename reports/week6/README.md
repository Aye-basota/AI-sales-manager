# Week 6 — Assignment 6 Sprint 4 Report

> **Status note:** this report reflects verified repository/GitHub state as of 2026-07-12. Several required artifacts are still open team action items and are marked **TODO** below rather than filled in with invented content — see [Open Items Before Submission](#open-items-before-submission).

## 1. Project

**Project name:** AI Sales Manager
**Short description:** Autonomous B2B outbound sales assistant using real Telegram accounts and LLM-driven dialogue to generate qualified meetings.

---

## 2. Backlog and Sprint Planning

- [Product Backlog board](https://github.com/users/Aye-basota/projects/1/views/1)
- [Sprint Backlog board](https://github.com/users/Aye-basota/projects/3/views/1?layout=board) (filtered to the Sprint 4 milestone)
- [Sprint 4 milestone](https://github.com/Aye-basota/AI-sales-manager/milestone/4)

### Sprint Goal

Enable a production-ready AI Sales Manager experience for the Week 6 trial release by delivering end-to-end lead management capabilities, including campaign execution, AI-driven conversations, analytics, and operational stability. The sprint aims to ensure the platform is ready for transition into real-world usage through a reliable user experience and stable production environment. (Source: [`docs/roadmap.md`](../../docs/roadmap.md#sprint-4--trial-release-readiness-and-production-stabilization))

### Sprint dates

2026-07-06 – 2026-07-12

### Scope summary

Selected Sprint 4 PBIs from the GitHub backlog ([milestone 4](https://github.com/Aye-basota/AI-sales-manager/milestone/4)):

| Issue | Type | Title | GitHub status |
|---|---|---|---|
| [#8](https://github.com/Aye-basota/AI-sales-manager/issues/8) | US | US-06 — Increase Lead Turnover | Open |
| [#9](https://github.com/Aye-basota/AI-sales-manager/issues/9) | US | US-07 — 24/7 Availability | Open |
| [#11](https://github.com/Aye-basota/AI-sales-manager/issues/11) | US | US-09 — Manual Dialog Takeover | Open |
| [#20](https://github.com/Aye-basota/AI-sales-manager/issues/20) | US | US-015 — Campaign Analytics and Conversion Dashboard | Open |
| [#68](https://github.com/Aye-basota/AI-sales-manager/issues/68) | US | US-019 — Improve Admin Panel Navigation | Open |
| [#23](https://github.com/Aye-basota/AI-sales-manager/issues/23) | Tech | TECH-03 — Manager Contact-Transfer Notification Flow | Open |
| [#26](https://github.com/Aye-basota/AI-sales-manager/issues/26) | Tech | TECH-06 — Track AI-Automation Rate per Dialog Session | Open |
| [#28](https://github.com/Aye-basota/AI-sales-manager/issues/28) | Tech | TECH-08 — CSV Contact Import: Persistence and Duplicate Handling | Open |
| [#53](https://github.com/Aye-basota/AI-sales-manager/issues/53) | Tech | TECH-11 — Deploy Application to Production VPS | Open |
| [#54](https://github.com/Aye-basota/AI-sales-manager/issues/54) | Tech | TECH-12 — Configure Production Infrastructure and Monitoring | Open |
| [#55](https://github.com/Aye-basota/AI-sales-manager/issues/55) | Tech | TECH-13 — Prompt Configuration and Versioning | Open |

**Note:** as of this report, all 11 Sprint 4 milestone issues are still open on GitHub even though the corresponding work has substantially shipped (see [§3](#3-delivered-product-changes) and `CHANGELOG.md`). The team should close or update these issues (e.g. via `closes #N` on the relevant PRs) so the milestone/board accurately reflects delivered work — see [Open Items](#open-items-before-submission).

### Total Sprint size

40 Story Points (23 SP user stories + 17 SP technical tasks). (Source: [`docs/roadmap.md`](../../docs/roadmap.md#sprint-4--trial-release-readiness-and-production-stabilization))

---

## 3. Delivered Product Changes

Per [`CHANGELOG.md`](../../CHANGELOG.md#040---2026-07-08) `[0.4.0]`:

- API metadata now identifies the Week 6 trial release as version `0.4.0`.
- Release automation verifies a SemVer tag points to a commit contained in `main` before publishing a GitHub Release.
- Seller MTProto read/typing actions use Pyrogram chat-level methods instead of raw peers with missing access hashes (fixes intermittent failures against unseen peers).
- Fixed release/profile deployments failing at startup when `DEBUG` is set to values like `release`, `prod`, or `production`.
- Fixed startup breaking when copied `.env.example` values (e.g. empty `TELEGRAM_API_ID`, placeholder `ADMIN_BOT_TOKEN`) are left in place.
- Inbound Telegram auto-replies now respect seller-account daily and 30-second rate limits and update account counters after sending.
- Guardrails now correctly detect emoji/symbol categories through Unicode metadata.
- **Security:** Telegram account API responses no longer expose stored `session_string` values.

Additional Sprint 4 work visible in the commit history but not yet reflected in `CHANGELOG.md`: a new lead-discovery feature using Telegram group/message parsing (TGStat-style search without a paid API), and a round of bot QA/dialogue hardening (chunked-message handling, character-consistency guardrails, admin script/runtime diagnostics). These should be added to `CHANGELOG.md` under `[Unreleased]` or a new release section before submission — see [Open Items](#open-items-before-submission).

---

## 4. Deployment and Run Instructions

- **Local:** `docker-compose up -d --build` then `docker-compose exec api alembic upgrade head`. Full walkthrough in [`LAUNCH_GUIDE.md`](../../LAUNCH_GUIDE.md).
- **Week 6 product access artifact:** the team introduced a production VPS deployment during Sprint 4, described in [`docs/customer-handover.md`](../../docs/customer-handover.md#deployment-and-access). Its address is intentionally **not published in this public repository** — it is shared directly with the customer and made available to instructors through the private submission channel, since the deployment sends real Telegram messages from a live account (see [`AGENTS.md`](../../AGENTS.md#safety-constraints)).
- **Open question about the VPS deployment:** the Week 6 Sprint Review surfaced a comment (see [`sprint-review-transcript.md`](sprint-review-transcript.md)) implying the bot's uptime depends on a laptop being on, which conflicts with the "always-on VPS" intent and with UAT-1's Pass result. This is unresolved as of this report — see [`sprint-review-summary.md`](sprint-review-summary.md#uat--customer-trial-results) and [Open Items](#open-items-before-submission).
- **Verification:** `GET /health` returns `status`, `db`, `scheduler`.

---

## 5. Customer-Facing Documentation

- [`README.md`](../../README.md)
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
- [`AGENTS.md`](../../AGENTS.md)
- [`docs/customer-handover.md`](../../docs/customer-handover.md)
- [Hosted documentation site](https://aye-basota.github.io/AI-sales-manager/)

### Customer-facing documentation review

**Not completed as of this report.** Assignment 6 Part 5.3 calls for asking the customer to review this documentation set during or before the Week 6 meeting. The 2026-07-12 session covered the product trial and transition-readiness discussion (see [§8](#8-uat-and-customer-trial-results)) but did not include a documentation walkthrough — `docs/customer-handover.md`'s own "Is the Current Documentation Sufficient?" section states this explicitly. This is an outstanding action item — see [Open Items](#open-items-before-submission).

---

## 6. Transition-Readiness Summary

Per [`docs/customer-handover.md#transition-status`](../../docs/customer-handover.md#transition-status), current as of the 2026-07-12 Sprint Review:

- **Handover level:** none of the three target levels (`Ready for independent use`, `Independently used by customer`, `Deployed or operated on customer side`) has been reached yet. The team demonstrated the product live and Mark used it directly during the session, but an unresolved contradiction about whether the deployment is actually independent of a team member's machine (see [§4](#4-deployment-and-run-instructions)) means the team is not yet claiming `Ready for independent use`.
- **Customer-confirmation status:** not yet `Accepted`. Mark gave positive verbal feedback during the session (off-record); written confirmation has not yet been collected.

**What must still happen in Week 7:**

1. Resolve or explain the VPS/local-machine uptime contradiction from the Week 6 demo.
2. Collect written customer confirmation, per Part 8 evidence requirements.
3. Complete the customer-facing documentation review with Mark (not done in the Week 6 session).
4. Create the Sprint 5 milestone and file the four follow-up issues identified below.
5. Move toward independent customer use or customer-side deployment/operation.

---

## 7. Customer Feedback Response

Per [`sprint-review-summary.md`](sprint-review-summary.md#customer-feedback--resulting-issues):

| Feedback point | Resulting action | Status |
|---|---|---|
| Lead-search/parsing quality needs improvement | Improve parsing result quality | **Not yet filed as a GitHub issue** — planned for Sprint 5 |
| Wants minimal-setup campaign start | Reduce manual configuration to start a campaign | **Not yet filed as a GitHub issue** — planned for Sprint 5 |
| Bot occasionally breaks character | Evaluate alternate LLM via existing routing API | **Not yet filed as a GitHub issue** — planned for Sprint 5 |
| Wants to test independently | Resolve production hosting stability (VPS) | **Not yet filed as a GitHub issue** — planned for Sprint 5 |

### Feedback not yet addressed

All four items above are unaddressed as of this report: no Sprint 5 milestone exists yet in the GitHub tracker, and no corresponding issues have been filed. This must happen before Week 6 submission closes out, per Assignment 6 Part 1 (explicit Sprint 5 milestone with selected or expected PBIs) — see [Open Items](#open-items-before-submission).

---

## 8. UAT and Customer Trial Results

Per [`sprint-review-summary.md`](sprint-review-summary.md#uat--customer-trial-results) (full scenarios in [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md)):

| Scenario | Result |
|---|---|
| UAT-1: 24/7 Production Availability via VPS Deployment | ✅ Pass as executed 2026-07-05 — **but see the open contradiction noted in [§4](#4-deployment-and-run-instructions) and [§6](#6-transition-readiness-summary)**, surfaced during the 2026-07-12 live demo |
| UAT-2: Natural Conversational Flow and Structured Lead Nurturing | ✅ Pass — assistant handled a pricing question with clarifying questions and stayed on-topic after an off-topic message |
| Lead discovery (new Sprint 4 feature, no UAT scenario yet) | ⚠️ Needs Improvement — customer explicitly flagged search/parsing quality as a gap |

**Recommendation for Sprint 5:** add UAT-3 (lead discovery) and UAT-4 (campaign analytics dashboard) to `docs/user-acceptance-tests.md`.

Full session transcript: [`sprint-review-transcript.md`](sprint-review-transcript.md). This is a raw, machine-transcribed recording rather than a cleaned/sanitized transcript — see [Open Items](#open-items-before-submission) for a flag on this before public submission.

---

## 9. Documentation Updated During Sprint 4

- [`docs/testing.md`](../../docs/testing.md) — test count and coverage figures updated (459 → 708 tests; coverage table reworked around current high-value/low-coverage modules; CI coverage gate documented as `--cov-fail-under=75`).
- [`docs/customer-handover.md`](../../docs/customer-handover.md) — created for Assignment 6 Parts 3–4, then updated with the Sprint 4 trial/VPS/transition status.
- [`docs/roadmap.md`](../../docs/roadmap.md) — Sprint 4 section added with goal, dates, scope, and story points.
- [`CHANGELOG.md`](../../CHANGELOG.md) — `[0.4.0]` entry added (see [§3](#3-delivered-product-changes)).

---

## 10. Release

[**`v0.4.0` — AI Sales Manager v0.4.0**](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.4.0) — the Week 6 trial / handover-candidate release for Assignment 6 Sprint 4. Tagged `v`-prefixed, points to a commit on `main`, and links the Sprint 4 milestone, this report, run/access instructions, `docs/customer-handover.md`, and `CHANGELOG.md`.

- [`CHANGELOG.md`](../../CHANGELOG.md)

---

## 11. Sprint Review

- Format: live product walkthrough + customer Q&A with Mark, 2026-07-12.
- Transcript: [`sprint-review-transcript.md`](sprint-review-transcript.md) (raw machine transcription — see [Open Items](#open-items-before-submission) regarding sanitization before treating this as the final public artifact).
- Summary: [`sprint-review-summary.md`](sprint-review-summary.md).

---

## 12. Team Reflection

- [`reflection.md`](reflection.md) — Week 6 reflection (Assignment 6 Part 12): trial release, customer meeting, transition blockers, Sprint 3 vs Sprint 4 analysis.
- [`retrospective.md`](retrospective.md) — Sprint 4 retrospective (Assignment 6 Part 11): what went well, gaps, comparison to Sprint 3 action points, Sprint 5 action points.
- [`llm-report.md`](llm-report.md) — LLM / AI usage disclosure (Assignment 6 Part 12).

---

## 13. Current Product Status and Expected Week 7 Follow-Up

**Current status:** the Week 6 trial demo ran successfully end-to-end (campaign setup, live AI conversation, lead discovery) on a production VPS deployment, and the customer engaged with it directly and gave positive informal feedback. Formal transition has not happened — no handover level has been reached yet, written customer confirmation is outstanding, and an unresolved question about the VPS deployment's actual independence from a team member's machine needs to be closed out.

**Expected Week 7 (Sprint 5) follow-up:**

1. Resolve the VPS/local-machine uptime contradiction (fix or clarify).
2. Create the Sprint 5 milestone and file the four customer-feedback issues.
3. Improve lead-discovery/parsing quality (top customer priority).
4. Improve prompt/response consistency (top customer priority).
5. Collect written customer confirmation and complete the customer-facing documentation review.
6. Create the `v0.4.0` release, then proceed toward `MVP v3` and final transition.

---

## 14. Contribution Traceability

| Team member | Issues | PRs/MRs | Reviews | Documentation / Reporting |
|---|---|---|---|---|
| [Aye-basota](https://github.com/Aye-basota) | — | [#77](https://github.com/Aye-basota/AI-sales-manager/pull/77) (Week 6 trial-release hardening, TECH-11/12/13-adjacent), [#81](https://github.com/Aye-basota/AI-sales-manager/pull/81) (test coverage hardening) | Approved [#77](https://github.com/Aye-basota/AI-sales-manager/pull/77) | — |
| [MuS0rKa](https://github.com/MuS0rKa) | — | [#75](https://github.com/Aye-basota/AI-sales-manager/pull/75), [#76](https://github.com/Aye-basota/AI-sales-manager/pull/76) (roadmap Sprint 4 planning) | Approved [#77](https://github.com/Aye-basota/AI-sales-manager/pull/77), [#78](https://github.com/Aye-basota/AI-sales-manager/pull/78), [#79](https://github.com/Aye-basota/AI-sales-manager/pull/79), [#80](https://github.com/Aye-basota/AI-sales-manager/pull/80), [#81](https://github.com/Aye-basota/AI-sales-manager/pull/81), [#82](https://github.com/Aye-basota/AI-sales-manager/pull/82)–[#85](https://github.com/Aye-basota/AI-sales-manager/pull/85) | `docs/roadmap.md` Sprint 4 section |
| [Volgadon636](https://github.com/Volgadon636) | — | [#79](https://github.com/Aye-basota/AI-sales-manager/pull/79), [#80](https://github.com/Aye-basota/AI-sales-manager/pull/80), [#82](https://github.com/Aye-basota/AI-sales-manager/pull/82)–[#85](https://github.com/Aye-basota/AI-sales-manager/pull/85) | — | Week 6 Sprint Review summary and transcript ([`sprint-review-summary.md`](sprint-review-summary.md), [`sprint-review-transcript.md`](sprint-review-transcript.md)) |
| [issammerdas05](https://github.com/issammerdas05) | — | [#78](https://github.com/Aye-basota/AI-sales-manager/pull/78) (CONTRIBUTING.md, AGENTS.md, customer-handover.md) | — | `docs/customer-handover.md`, `README.md` (Week 6 currency updates), this report, restored `reports/week5/` files, [`llm-report.md`](llm-report.md) partial disclosure |
| [Markyl018](https://github.com/Markyl018) | — | — | — | **TODO — no Sprint 4 activity found via GitHub PRs/issues/reviews as of this report; confirm and fill in.** |

*Table built from merged PRs and reviews visible in the public GitHub history for Sprint 4 (2026-07-06 – 2026-07-12), via the GitHub REST API. Not every commit is individually attributed; see the repository commit history for full detail. Issue-level attribution is sparse this sprint because Sprint 4 milestone issues remain open (see [§2](#2-backlog-and-sprint-planning)) rather than closed via PR references.*

---

## 15. Screenshots

**Not yet captured — placeholder only.** Place screenshots in `reports/week6/images/` and embed them here before submission:

- `sprint-milestone.png` — [Sprint 4 milestone](https://github.com/Aye-basota/AI-sales-manager/milestone/4) view
- `sprint-backlog-board.png` — Sprint Backlog board filtered to Sprint 4
- `reviewed-pr.png` — an example issue-linked, reviewed PR (e.g. [#77](https://github.com/Aye-basota/AI-sales-manager/pull/77) or [#78](https://github.com/Aye-basota/AI-sales-manager/pull/78))
- `product-access.png` — the Week 6 trial deployment (sanitized, no real customer data/session strings visible)
- `ci-latest-run.png` — latest CI run on `main`

---

## Open Items Before Submission

This report intentionally surfaces gaps rather than papering over them. Before the Week 6 submission deadline, the team still needs to:

1. ~~Create the `v0.4.0` SemVer release~~ — **done**, see [§10](#10-release).
2. **Resolve or explain the VPS/local-machine uptime contradiction** surfaced in the Week 6 demo — see [§4](#4-deployment-and-run-instructions), [§6](#6-transition-readiness-summary), [§8](#8-uat-and-customer-trial-results).
3. **Create the Sprint 5 milestone and file the four customer-feedback issues** — see [§7](#7-customer-feedback-response).
4. **Complete the customer-facing documentation review with the customer** — see [§5](#5-customer-facing-documentation).
5. **Collect written customer confirmation** of the Week 6 status, per Part 8.
6. **Decide on transcript handling**: [`sprint-review-transcript.md`](sprint-review-transcript.md) is a raw, unsanitized machine transcription (informal team banter, real first names, imperfect translation) rather than a cleaned English transcript. Confirm this is what the team intends to publish in the public repository, or replace it with a sanitized version / move it to the private Moodle-only submission channel instead, per the shared transcript publication rules.
7. **Capture and embed screenshots** — see [§15](#15-screenshots).
8. **Close or update the 11 Sprint 4 milestone issues** on GitHub to reflect delivered work — see [§2](#2-backlog-and-sprint-planning).
9. **Add the lead-discovery feature and bot-hardening work to `CHANGELOG.md`** if not already covered by `[0.4.0]` — see [§3](#3-delivered-product-changes).
10. **Fix the Week 5/Week 6 mislabeling in `llm-report.md`** — it was committed as a copy of `reports/week5/llm-report.md`; see the `week6-llm-report-fix` branch for a proposed correction.
