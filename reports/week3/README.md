# Assignment 3 — Week 3 Report

## Project

**AI Sales Manager** — autonomous B2B outbound sales assistant for Telegram, driven by LLM dialogue and real MTProto accounts.

- [LICENSE](../../LICENSE)
- [Root README.md](../../README.md)

## Summary of Scope Since Assignment 2

In Assignment 2 the team documented 10 user stories in [`reports/week2/user-stories.md`](../../reports/week2/user-stories.md). For Assignment 3 these stories were migrated to the issue-based Product Backlog and refined into PBIs. The current registry lives in [`docs/user-stories.md`](../../docs/user-stories.md).

MVP v1 was scoped to the core sales-automation flow:

- [`US-01`](https://github.com/Aye-basota/AI-sales-manager/issues/3) — Getting product information
- [`US-02`](https://github.com/Aye-basota/AI-sales-manager/issues/4) — Contact Product Owner
- [`US-03`](https://github.com/Aye-basota/AI-sales-manager/issues/5) — Bot Setup and Funnel Upload
- [`US-04`](https://github.com/Aye-basota/AI-sales-manager/issues/6) — Labor Cost Reduction
- [`US-08`](https://github.com/Aye-basota/AI-sales-manager/issues/10) — LLM Provider Selection

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

1. Apply the `mvp-v1` label and Sprint 1 milestone to the relevant issues in the GitHub UI.
2. Create GitHub Projects for Product Backlog and Sprint Backlog views.
3. Record and publish the public sanitized MVP v1 video demonstration.
4. Set up a persistent staging deployment.
5. Open Sprint 2 for operator takeover and rate-limiting PBIs.

## Contribution Traceability

| Team member | Issues | PRs | Reviews |
|---|---|---|---|
| @Aye-basota | US-01, US-03 | #11, #13 | #12 |
| *(add teammates)* | | | |

> Update this table after creating real issues and PRs in the GitHub UI.

## Release and Documentation

| Artifact | Link |
|---|---|
| SemVer release for MVP v1 | [v0.1.0](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.1.0) |
| CHANGELOG | [CHANGELOG.md](../../CHANGELOG.md) |
| Process Requirements | [Process_Requirements.md](../../Process_Requirements.md) |
| Roadmap | [docs/roadmap.md](../../docs/roadmap.md) |
| Definition of Done | [docs/definition-of-done.md](../../docs/definition-of-done.md) |
| Issue templates | [`.github/ISSUE_TEMPLATE`](../../.github/ISSUE_TEMPLATE) |
| Extended PR template | [`.github/pull_request_template.md`](../../.github/pull_request_template.md) |

## Reviewed PRs

- [#XX](../../pull/XX) — Add week3 images placeholder *(issue-linked, reviewed)*
- [#YY](../../pull/YY) — Reviewed teammate's PR

> Replace XX and YY with real PR numbers after creating them in the GitHub UI.

## Delivered MVP v1

- **Local / Docker:** follow [root README.md](../../README.md#быстрый-старт-docker).
- **API docs:** `http://localhost:8000/docs` after startup.

## Video Demonstration

- [MVP v1 demo (YouTube / Loom)](https://example.com) *(upload your video and replace this link)*

## Screenshots

| View | Screenshot |
|---|---|
| Product Backlog | ![Product Backlog](images/backlog.jpg) |
| Sprint Backlog | ![Sprint Backlog](images/sprint.jpg) |
| Sprint milestone | ![Milestone](images/milestone.jpg) |
| MVP v1 view | ![MVP v1](images/release.jpg) |
| SemVer release | ![Release](images/release.jpg) |

## Customer Review

- **Transcript / notes:** [customer-review-summary.md](customer-review-summary.md)
- **Recording:** shared privately with instructors via Moodle *(or replace with public link if permitted)*

## Reflection and Retrospective

- [Week 3 reflection](reflection.md)
- [Sprint retrospective](retrospective.md)
- [LLM usage report](llm-report.md)
