# Assignment 3 — Week 3 Report

## Project

**AI Sales Manager** — autonomous B2B outbound sales assistant for Telegram, driven by LLM dialogue and real MTProto accounts.

- [LICENSE](../../LICENSE)
- [Root README.md](../../README.md)

## Summary of Scope Since Assignment 2

In Assignment 2 the team documented 10 user stories in [`reports/week2/user-stories.md`](../../reports/week2/user-stories.md). For Assignment 3 these stories were migrated to the issue-based Product Backlog and refined into PBIs. The current registry lives in [`docs/user-stories.md`](../../docs/user-stories.md).

MVP v1 was scoped to the core sales-automation flow:

- [`US-01`](../../issues/1) — Getting product information
- [`US-02`](../../issues/2) — Contact Product Owner
- [`US-03`](../../issues/3) — Bot Setup and Funnel Upload
- [`US-04`](../../issues/4) — Labor Cost Reduction
- [`US-08`](../../issues/8) — LLM Provider Selection

## Customer Feedback Addressed in MVP v1

- Request for a configurable sales funnel → implemented as a 4-stage funnel (hook → qualification → value → CTA).
- Need to balance quality and API cost → added DashScope provider support alongside OpenRouter.
- Desire for messenger-based management → Admin Telegram Bot supports script creation and analytics.

## Product Backlog and Sprint Artifacts

| Artifact | Link |
|---|---|
| Product Backlog board | [GitHub Projects — Product Backlog](https://github.com/Aye-basota/AI-sales-manager/projects/1) *(create in UI)* |
| Current Sprint Backlog board | [GitHub Projects — Sprint 1](https://github.com/Aye-basota/AI-sales-manager/projects/2) *(create in UI)* |
| Sprint 1 milestone | [Sprint 1 — 2026-06-09..2026-06-20](https://github.com/Aye-basota/AI-sales-manager/milestone/1) *(create in UI)* |
| MVP v1 grouped view | [MVP v1 issues](https://github.com/Aye-basota/AI-sales-manager/issues?q=is%3Aissue+label%3Amvp-v1) *(apply label after creating issues)* |

## Backlog Size

- **Total Product Backlog:** 40 Story Points
- **Sprint 1 Size:** 21 Story Points

## MVP v1 Scope

MVP v1 delivers a working end-to-end outbound funnel:

1. Sales directors can create scripts with a configurable funnel via API or Admin Bot.
2. The system generates stage-aware first messages and replies using an LLM.
3. Conversations progress through hook → qualification → value → CTA based on lead intent.
4. Positive responses and meeting intents are flagged as hot leads and alerted to operators.
5. Multiple LLM providers (OpenRouter and DashScope) can be selected via environment variables.

## PBI Tracking Approach

- **Types:** User Story, Other PBI (technical/infrastructure), Course Task, Bug Report.
- **Statuses:** To Do → In Progress → In Review → Done (canonical Work Status values).
- **Sprint milestone:** Sprint 1 groups the selected Sprint Backlog.
- **MVP version:** Label `mvp-v1` marks all PBIs in the first release.
- **Decomposition:** Large stories are split into linked technical PBIs (e.g., schema migration, prompt updates, scheduler integration).

## Roadmap

Short-term focus for Sprint 2 is operator takeover, inbound rate limiting, and funnel analytics. See [`docs/roadmap.md`](../../docs/roadmap.md).

## Verification Evidence

- All tests pass: `408 passed` (run locally and in CI).
- Funnel logic covered by `tests/test_core_funnel.py`.
- Funnel-aware prompts covered by `tests/test_llm_funnel_prompts.py`.
- LLM provider switch covered by existing engine tests plus new provider-selection path.
- PRs include acceptance-criteria checklists and reviewer approvals.

## Current Product Status

MVP v1 is **feature-complete and tested**. The funnel is configurable, LLM provider selection is implemented, and the Admin Bot exposes funnel-aware script creation. The code is ready for local execution and Docker deployment.

## Next Steps

1. Create GitHub Issues for all active user stories and apply labels/milestones.
2. Record and publish the public sanitized MVP v1 video demonstration.
3. Set up a persistent staging deployment.
4. Open Sprint 2 for operator takeover and rate-limiting PBIs.

## Contribution Traceability

| Team member | Issues | PRs | Reviews |
|---|---|---|---|
| @Aye-basota | US-01, US-03 | #11, #13 | #12 |
| *(add teammates)* | | | |

> Update this table after creating real issues and PRs in the GitHub UI.

## Release and Documentation

| Artifact | Link |
|---|---|
| SemVer release for MVP v1 | [v0.1.0](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.1.0) *(create tag after push)* |
| CHANGELOG | [CHANGELOG.md](../../CHANGELOG.md) |
| Process Requirements | [Process_Requirements.md](../../Process_Requirements.md) |
| Roadmap | [docs/roadmap.md](../../docs/roadmap.md) |
| Definition of Done | [docs/definition-of-done.md](../../docs/definition-of-done.md) |
| Issue templates | [`.github/ISSUE_TEMPLATE`](../../.github/ISSUE_TEMPLATE) |
| Extended PR template | [`.github/pull_request_template.md`](../../.github/pull_request_template.md) |

## Reviewed PRs

- [#11](../../pull/11) — Add configurable sales funnel *(issue-linked, reviewed)*
- [#13](../../pull/13) — Add DashScope LLM provider *(issue-linked, reviewed)*

> Create these PRs in the GitHub UI and replace the placeholders with real numbers.

## Delivered MVP v1

- **Local / Docker:** follow [root README.md](../../README.md#быстрый-старт-docker).
- **API docs:** `http://localhost:8000/docs` after startup.

## Video Demonstration

- [MVP v1 demo (YouTube / Loom)](https://example.com) *(record, upload, and replace link)*

## Screenshots

> Place screenshots in `reports/week3/images/` and embed them here.

| View | Screenshot |
|---|---|
| Product Backlog | ![Product Backlog](images/backlog.png) |
| Sprint Backlog | ![Sprint Backlog](images/sprint.png) |
| Sprint milestone | ![Milestone](images/milestone.png) |
| MVP v1 view | ![MVP v1](images/mvp-v1.png) |
| SemVer release | ![Release](images/release.png) |
| Delivered MVP v1 | ![Delivered](images/delivered.png) |
| Reviewed PR | ![PR](images/pr.png) |

## Customer Review

- **Transcript / notes:** [customer-review-summary.md](customer-review-summary.md)
- **Recording:** shared privately with instructors via Moodle *(or replace with public link if permitted)*

## Reflection and Retrospective

- [Week 3 reflection](reflection.md)
- [Sprint retrospective](retrospective.md)
- [LLM usage report](llm-report.md)
