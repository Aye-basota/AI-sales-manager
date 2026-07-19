# Week 7 Report - Sprint 5 / MVP v3

AI Sales Manager is a Telegram-based B2B outbound sales assistant that uses real Telegram accounts and LLM-generated dialogue to launch campaigns, respond to leads, and notify operators about high-intent conversations.

This Week 7 index is the final Assignment 6 public submission index for Sprint 5, final transition evidence, and `MVP v3`. The complete Week 6 trial-release evidence is linked from [`reports/week6/README.md`](../week6/README.md).

## Boards, Milestone, and Sprint Scope

- Week 6 public report: [`reports/week6/README.md`](../week6/README.md)
- Product Backlog board: [GitHub Projects - Product Backlog](https://github.com/users/Aye-basota/projects/1/views/1)
- Sprint 5 Backlog board/view: [GitHub Projects - Sprint Board](https://github.com/users/Aye-basota/projects/2)
- Sprint 5 milestone: [Sprint 5](https://github.com/Aye-basota/AI-sales-manager/milestone/5)
- Sprint 5 dates: 2026-07-13 - 2026-07-19
- Sprint 5 Goal: respond to Week 6 trial feedback, reduce the highest-risk follow-up/dialogue issues, keep tests and CI current, and deliver the final course version `MVP v3`.
- Sprint 5 size: 28 Story Points, as documented in the Sprint 5 milestone.

Sprint 5 follow-up scope:

| Week 6 feedback / risk | Sprint 5 response | Evidence |
|---|---|---|
| Bot could repeat itself or send weak second-first-touch follow-ups. | Added follow-up quality gates, retry prompt, safe fallback, and stricter one-follow-up eligibility. | [`app/core/follow_up_quality.py`](../../app/core/follow_up_quality.py), [`app/core/scheduler.py`](../../app/core/scheduler.py), [`tests/test_core_follow_up_quality.py`](../../tests/test_core_follow_up_quality.py), [`tests/test_core_scheduler.py`](../../tests/test_core_scheduler.py) |
| Approved preview text could differ from the message actually sent. | Stored approved preview text per queued contact and reused it during scheduler send. | [`app/bots/admin_bot.py`](../../app/bots/admin_bot.py), [`app/models/campaign.py`](../../app/models/campaign.py), [`alembic/versions/20260715_campaign_contact_preview_message.py`](../../alembic/versions/20260715_campaign_contact_preview_message.py) |
| Replies needed more verified context and less role-breaking behavior. | Added business-owner clarification, verified-fact context, conservative unknown-fact handling, and safer deterministic fallbacks. | [`app/core/business_knowledge.py`](../../app/core/business_knowledge.py), [`app/bots/inbound_listener.py`](../../app/bots/inbound_listener.py), [`app/bots/admin_bot.py`](../../app/bots/admin_bot.py), [`tests/test_business_knowledge.py`](../../tests/test_business_knowledge.py) |
| Follow-up fixes must not weaken quality gates or CI. | Added/updated regression tests and architecture/testing docs for changed areas. | [`docs/testing.md`](../../docs/testing.md), [`docs/architecture/README.md`](../../docs/architecture/README.md), [`docs/architecture/adr/ADR-003.md`](../../docs/architecture/adr/ADR-003.md) |

## Final Product Access and Handover

- Final product access artifact: [@salesmanager228_bot](https://t.me/salesmanager228_bot)
- Current access/run instructions: [`README.md`](../../README.md) and [`LAUNCH_GUIDE.md`](../../LAUNCH_GUIDE.md)
- Maintained handover document: [`docs/customer-handover.md`](../../docs/customer-handover.md)
- Hosted documentation site: [aye-basota.github.io/AI-sales-manager](https://aye-basota.github.io/AI-sales-manager/)
- Contributor guidance: [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
- Agent guidance: [`AGENTS.md`](../../AGENTS.md)
- Roadmap: [`docs/roadmap.md`](../../docs/roadmap.md)
- Changelog: [`CHANGELOG.md`](../../CHANGELOG.md)

Final transition outcome:

| Required statement | Current public status |
|---|---|
| Handover level reached | `Independently used by customer` |
| Customer-confirmation status | `Accepted with follow-up items` |
| Transferred / made available | Public repository, hosted docs, reproducible Docker setup, final bot access path |
| Retained by team | GitHub repository administration, live bot/deployment operation, Telegram/LLM credentials |
| Customer-side operation | Not reached in Week 7; documented as a follow-up self-hosting path |

The customer independently tested the product using the admin panel, his own test contacts, a live conversation with the bot, lead search, and analytics. He accepted the product for the reached handover level, while the team keeps documentation clarity, minimal-setup campaign-launch re-test, and optional customer-owned hosting as visible follow-up items in [`docs/customer-handover.md`](../../docs/customer-handover.md).

## MVP v3 Release and Demo Video

- Final SemVer release: [`v0.5.0`](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.5.0)
- Week 6 trial release: [`v0.4.0`](https://github.com/Aye-basota/AI-sales-manager/releases/tag/v0.4.0)
- API metadata: `0.5.0`
- Public sanitized demo video: external upload required before final submission; add the public URL here and to the `v0.5.0` GitHub Release.

The `v0.5.0` release must be published from the protected `main` commit after the final fixes PR is merged, and the release body must link the Sprint 5 milestone, current access/run instructions, [`docs/customer-handover.md`](../../docs/customer-handover.md), this Week 7 report, and the public sanitized demo video.

## Week 7 UAT and Customer Feedback

Relevant maintained UAT scenarios are in [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md).

| Scenario | Week 7 result | Public evidence |
|---|---|---|
| UAT-001: 24/7 production availability via VPS/team-operated deployment | Pass, reconfirmed through accessible product during independent testing and the Week 7 call | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md) |
| UAT-002: Natural conversational flow and lead nurturing | Pass, reinforced by customer feedback that prompt quality was noticeably improved and no role-breaking was observed | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md), [`sprint-review-summary.md`](sprint-review-summary.md) |
| UAT-003: Lead-discovery result quality | Pass after Week 7 re-run; customer found relevant leads without repeated broadening | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md), [`sprint-review-summary.md`](sprint-review-summary.md) |
| UAT-004: Campaign analytics dashboard accuracy | Pass; customer reviewed reply rate, hot leads, and automation rate | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md), [`sprint-review-summary.md`](sprint-review-summary.md) |
| UAT-005: Minimal-setup campaign launch | Needs Improvement; not explicitly re-tested in Week 7 | [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md) |

Customer feedback response:

| Feedback / follow-up item | Sprint 5 result | Current disposition |
|---|---|---|
| Lead-search/parsing quality needs improvement | Customer confirmed Week 7 results were more relevant | Resolved for `MVP v3`; reconcile/close issue [#90](https://github.com/Aye-basota/AI-sales-manager/issues/90) before submission |
| Overall prompt/response quality and role-breaking risk | Customer confirmed responses were noticeably better and no role-breaking was observed | Resolved for `MVP v3`; issue [#92](https://github.com/Aye-basota/AI-sales-manager/issues/92) is closed |
| Campaign setup should require less manual friction | Not explicitly re-tested during Week 7 confirmation | Follow-up item tied to UAT-005 and issue [#68](https://github.com/Aye-basota/AI-sales-manager/issues/68) |
| Handover documentation was not fully clear on first read | Logged in the handover document | Follow-up item under `Accepted with follow-up items` |
| Customer-owned hosting/deployment | Customer plans to set it up later | Follow-up beyond the reached handover level |

## Maintained Documentation Updated for Sprint 5

- [`README.md`](../../README.md)
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
- [`AGENTS.md`](../../AGENTS.md)
- [`docs/customer-handover.md`](../../docs/customer-handover.md)
- [`docs/roadmap.md`](../../docs/roadmap.md)
- [`docs/development-process.md`](../../docs/development-process.md)
- [`docs/definition-of-done.md`](../../docs/definition-of-done.md)
- [`docs/testing.md`](../../docs/testing.md)
- [`docs/quality-requirements.md`](../../docs/quality-requirements.md)
- [`docs/quality-requirement-tests.md`](../../docs/quality-requirement-tests.md)
- [`docs/user-acceptance-tests.md`](../../docs/user-acceptance-tests.md)
- [`docs/architecture/README.md`](../../docs/architecture/README.md)

## Sprint Review, Retrospective, Reflection, and LLM Usage

- Published sanitized Sprint Review transcript: [`sprint-review-transcript.md`](sprint-review-transcript.md)
- Sprint Review summary: [`sprint-review-summary.md`](sprint-review-summary.md)
- Retrospective: [`retrospective.md`](retrospective.md)
- Reflection: [`reflection.md`](reflection.md)
- LLM report: [`llm-report.md`](llm-report.md)

Private recording links, exact timecodes, access credentials, and written customer-confirmation screenshots belong only in the Week 7 Moodle PDF.

## Demo Day Preparation

The Week 7 rehearsal/presentation preparation is handled through the private Week 7 Moodle submission because the slide deck PDF and rehearsed presentation video must not be committed publicly. The public report records that Demo Day preparation is required; the private Moodle wrapper must provide the slide deck, rehearsal evidence, and access links.

## Final Product Status

`MVP v3` is the final Assignment 6 course version. The product is accessible through [@salesmanager228_bot](https://t.me/salesmanager228_bot), reproducible from the repository using Docker, and independently tested by the customer. The final public claim is `Independently used by customer` with customer-confirmation status `Accepted with follow-up items`.

## Contribution Traceability

| Contributor / scope | Evidence |
|---|---|
| Sprint 5 follow-up fixes, tests, release/handover prep | PR [#96](https://github.com/Aye-basota/AI-sales-manager/pull/96), prompt/response-quality follow-up [#92](https://github.com/Aye-basota/AI-sales-manager/issues/92), lead-discovery follow-up [#90](https://github.com/Aye-basota/AI-sales-manager/issues/90), and prompt-versioning trace [#55](https://github.com/Aye-basota/AI-sales-manager/issues/55) |
| Week 7 Parts 10-12 report artefacts | [`sprint-review-summary.md`](sprint-review-summary.md), [`sprint-review-transcript.md`](sprint-review-transcript.md), [`retrospective.md`](retrospective.md), [`reflection.md`](reflection.md), [`llm-report.md`](llm-report.md), issues [#102](https://github.com/Aye-basota/AI-sales-manager/issues/102) and [#103](https://github.com/Aye-basota/AI-sales-manager/issues/103) |
| Week 6 evidence baseline | [`reports/week6/README.md`](../week6/README.md) and PR [#95](https://github.com/Aye-basota/AI-sales-manager/pull/95) |

## Screenshots

Assignment 6 asks for embedded Week 7 screenshots when public links may not be reliably inspectable. Add sanitized screenshots under `reports/week7/images/` before final Moodle submission for:

- Sprint 5 milestone / Sprint Backlog state
- final `v0.5.0` release
- final product access or deployment evidence
- example reviewed issue-linked PR
- public sanitized demo video page, if the video platform is not reliably inspectable
