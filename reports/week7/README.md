# Week 7 Report - Sprint 5 / MVP v3

AI Sales Manager is a Telegram-based B2B outbound sales assistant that uses real Telegram accounts and LLM-generated dialogue to launch campaigns, respond to leads, and notify operators about high-intent conversations.

This Week 7 index is scoped to the final Sprint 5 follow-up maintenance and `MVP v3` transition/release evidence. The complete Week 6 trial-release evidence remains in [`reports/week6/README.md`](../week6/README.md).

## 1. Boards, Milestone, and Sprint Scope

- Product Backlog / project board: [AI Sales Manager GitHub issues](https://github.com/Aye-basota/AI-sales-manager/issues)
- Sprint 5 Backlog / milestone: [Sprint 5 milestone](https://github.com/Aye-basota/AI-sales-manager/milestone/5)
- Sprint 5 dates: 2026-07-13 - 2026-07-19
- Sprint 5 Goal: respond to Week 6 trial feedback, reduce the highest-risk follow-up/dialogue issues, keep tests and CI current, and deliver the final course version `MVP v3`.
- Sprint 5 size: documented in the Sprint 5 GitHub milestone as the authoritative Sprint Backlog container.

Sprint 5 follow-up scope used by this PR:

| Week 6 feedback / risk | Sprint 5 response | Evidence |
|---|---|---|
| Bot could repeat itself or send weak second-first-touch follow-ups. | Added follow-up quality gates, retry prompt, safe fallback, and stricter one-follow-up eligibility. | [`app/core/follow_up_quality.py`](../../app/core/follow_up_quality.py), [`app/core/scheduler.py`](../../app/core/scheduler.py), [`tests/test_core_follow_up_quality.py`](../../tests/test_core_follow_up_quality.py), [`tests/test_core_scheduler.py`](../../tests/test_core_scheduler.py) |
| Approved preview text could differ from the message actually sent. | Stored approved preview text per queued contact and reused it during scheduler send. | [`app/bots/admin_bot.py`](../../app/bots/admin_bot.py), [`app/models/campaign.py`](../../app/models/campaign.py), [`alembic/versions/20260715_campaign_contact_preview_message.py`](../../alembic/versions/20260715_campaign_contact_preview_message.py) |
| Replies needed more context and less role-breaking behavior. | Passed recent dialogue as real chat messages, shortened prompts around latest lead intent, and improved deterministic fallbacks for pricing/basic-condition questions. | [`app/llm/prompts.py`](../../app/llm/prompts.py), [`app/bots/inbound_listener.py`](../../app/bots/inbound_listener.py), [`app/config/prompts/v1.json`](../../app/config/prompts/v1.json), [`tests/test_llm_prompts.py`](../../tests/test_llm_prompts.py) |
| Follow-up fixes must not weaken quality gates or CI. | Added/updated regression tests and architecture/testing docs for changed areas. | [`docs/testing.md`](../../docs/testing.md), [`docs/architecture/README.md`](../../docs/architecture/README.md), [`docs/architecture/adr/ADR-003.md`](../../docs/architecture/adr/ADR-003.md) |

## 2. Final Product Access and Handover

- Final product access artifact: [@salesmanager228_bot](https://t.me/salesmanager228_bot)
- Current access/run instructions: [`README.md`](../../README.md) and [`LAUNCH_GUIDE.md`](../../LAUNCH_GUIDE.md)
- Maintained handover document: [`docs/customer-handover.md`](../../docs/customer-handover.md)
- Hosted documentation site: [aye-basota.github.io/AI-sales-manager](https://aye-basota.github.io/AI-sales-manager/)
- Contributor guidance: [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
- Agent guidance: [`AGENTS.md`](../../AGENTS.md)

Final transition outcome:

| Required statement | Current public status |
|---|---|
| Handover level reached | `Ready for independent use` |
| Customer-confirmation status | `Accepted with follow-up items` |
| Transferred / made available | Public repository, hosted docs, reproducible Docker setup, final bot access path |
| Retained by team | GitHub repository administration, live bot/deployment operation, Telegram/LLM credentials |
| Optional stronger transition path | Customer-owned deployment/operation using the same Docker and environment-variable setup |

The final public transition claim is clear and inspectable: the product is accessible for customer/TA evaluation through the Telegram bot, reproducible from the repository, and accepted with follow-up items for quality and longer-term operation improvements.

## 3. MVP v3 Release

- Final SemVer release target: [`v0.5.0`](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.5.0)
- Required target: a commit on protected `main` after this PR is merged.
- Week 6 trial release: [`v0.4.0`](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.4.0)
- Changelog: [`CHANGELOG.md`](../../CHANGELOG.md)
- API metadata: `0.5.0`
- Public sanitized demo video: owned by Assignment 6 Part 14 and linked from the final `v0.5.0` release before submission.

Release checklist for the `v0.5.0` GitHub Release:

- Tag: `v0.5.0`
- Target: latest protected `main` commit after this PR is merged
- Title: `AI Sales Manager v0.5.0 - MVP v3`
- Include links to:
  - Sprint 5 milestone
  - [@salesmanager228_bot](https://t.me/salesmanager228_bot)
  - [`docs/customer-handover.md`](../../docs/customer-handover.md)
  - [`reports/week7/README.md`](README.md)
  - public sanitized demo video

## 4. Week 7 UAT and Quality Evidence

Relevant maintained UAT scenarios are in [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md). For this Sprint 5 follow-up scope, automated regression coverage is the main inspectable public evidence, complemented by the Week 7 customer confirmation/recording evidence in the private submission channel.

Key Sprint 5 regression areas:

- follow-up quality gate and fallback behavior
- one-follow-up scheduler eligibility
- no stale sends after replies or operator intervention
- approved preview reuse during actual send
- context-aware inbound reply prompts and deterministic fallbacks
- humanized chunked message sending

## 5. Links Owned by Other Week 7 Parts

These files are required for the full Week 7 submission index and are reserved for the teammates responsible for those Week 7 evidence parts:

- Sprint Review transcript or notes: `reports/week7/sprint-review-transcript.md` or `reports/week7/sprint-review-notes.md`
- Sprint Review summary: `reports/week7/sprint-review-summary.md`
- Reflection (Part 12): `reports/week7/reflection.md`
- Retrospective (Part 11): `reports/week7/retrospective.md`
- LLM report (Part 12): `reports/week7/llm-report.md`
- Public sanitized demo video link
- Week 7 rehearsal/presentation evidence
- Week 7 screenshots under `reports/week7/images/`

## 6. Final Product Status

`MVP v3` is prepared as the final Assignment 6 release candidate with Sprint 5 maintenance focused on dialogue correctness, follow-up safety, preview/send consistency, and traceable regression coverage. Final submission packaging adds the Sprint 5 milestone evidence, the final `v0.5.0` release after merge, public demo video link, and private Week 7 confirmation evidence.

## 7. Contribution Traceability for This Scope

| Contributor / scope | Evidence |
|---|---|
| Sprint 5 follow-up fixes, tests, release/handover prep | PR [#96](https://github.com/Aye-basota/AI-sales-manager/pull/96), closing prompt/response-quality follow-up [#92](https://github.com/Aye-basota/AI-sales-manager/issues/92), referencing lead-discovery follow-up [#90](https://github.com/Aye-basota/AI-sales-manager/issues/90), and preserving the Week 6 prompt-versioning trace to [#55](https://github.com/Aye-basota/AI-sales-manager/issues/55). |
| Week 6 evidence baseline | [`reports/week6/README.md`](../week6/README.md) and PR [#95](https://github.com/Aye-basota/AI-sales-manager/pull/95) |
