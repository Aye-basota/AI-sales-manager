# Sprint 4 Review Summary — Week 6

**Sprint Goal (from [`docs/roadmap.md`](../../docs/roadmap.md)):** Enable a production-ready AI Sales Manager experience for the Week 6 trial release by delivering end-to-end lead management capabilities, including campaign execution, AI-driven conversations, analytics, and operational stability. The sprint aims to ensure the platform is ready for transition into real-world usage through a reliable user experience and stable production environment.

**Format:** Live product walkthrough + customer Q&A with Mark, July 12, 2026. Full transcript: [`sprint-review-transcript.md`](./sprint-review-transcript.md).

## What was reviewed
The team demonstrated the current product end-to-end: business/campaign management, funnel configuration, a live conversation with the AI (including typing-delay and anti-spam behavior), and a new lead-discovery feature that finds prospects via Telegram group parsing and exports them in a campaign-ready format.

## UAT / customer-trial results
Two maintained UAT scenarios are current (`docs/user-acceptance-tests.md`, Sprint 3 / MVP v2, last executed 2026-07-05 with Mark):

| Scenario | Result |
|---|---|
| UAT-1: Verify 24/7 Production Availability via VPS Deployment | ✅ Pass — Mark confirmed the bot responded correctly with both the local dev machine and Docker fully shut down |
| UAT-2: Verify Natural Conversational Flow and Structured Lead Nurturing | ✅ Pass — assistant handled a pricing question with clarifying questions instead of a flat answer, and stayed on-topic after an off-topic message |

**Open issue:** the July 12 live demo implied the bot's uptime depends on a local machine — this conflicts with UAT-1's Pass result and needs to be resolved/explained before Week 7 (see notes for details).

No new maintained UAT scenarios exist yet for the Sprint 4 features shown live on July 12 (lead-discovery via group parsing, campaign analytics dashboard, manual dialog takeover). Recommend adding UAT-3 (lead discovery) and UAT-4 (analytics dashboard) to `docs/user-acceptance-tests.md` for Sprint 5 — lead-discovery in particular should probably be logged as **Needs Improvement** rather than Pass, since Mark explicitly flagged its quality as a gap.

## Customer feedback → resulting issues
| Feedback | Resulting action |
|---|---|
| Lead-search/parsing quality needs improvement | New issue: improve parsing result quality |
| Wants minimal-setup campaign start | New issue: reduce manual configuration to start a campaign |
| Bot occasionally breaks character | New issue: evaluate alternate LLM via existing routing API |
| Wants to test independently | New issue: resolve production hosting stability (VPS) |

## Follow-up for Sprint 5
See the four items above, to be created as GitHub issues and assigned to the Sprint 5 milestone.

## Handover status as of Week 6
- **Handover level reached:** None of the three target levels yet — live demo and access-sharing completed; independent use is the Week 7 target, blocked pending resolution of the VPS hosting status conflict above.
- **Customer-confirmation status:** Informally positive (verbal, off-record, same day) — Mark is satisfied overall, with two priorities: better prompt/response quality and stronger lead search. **Written confirmation is still needed** as private evidence for Part 8 — a short text message is sufficient.
