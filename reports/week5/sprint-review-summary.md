# Sprint 4 Review Summary — Week 6

**Sprint Goal:** Deliver a production-ready experience for the Week 6 trial — reliable campaign execution, AI-driven conversations, analytics, and operational stability.

**Format:** Live product walkthrough + customer Q&A with Mark, July 12, 2026.

## What was reviewed

The team demonstrated the current product end-to-end: business/campaign management, funnel configuration, a live conversation with the AI (including typing-delay and anti-spam behavior), and a new lead-discovery feature that finds prospects via Telegram group parsing and exports them in a campaign-ready format. The product was demoed running on the production VPS, confirmed independent of any team member's local machine.

## UAT / customer-trial results

Two maintained UAT scenarios are current (`docs/user-acceptance-tests.md`, Sprint 3 / MVP v2, last executed 2026-07-05 with Mark):

| Scenario | Result |
|---|---|
| UAT-1: Verify 24/7 Production Availability via VPS Deployment | ✅ Pass — Mark confirmed the bot responded correctly with both the local dev machine and Docker fully shut down |
| UAT-2: Verify Natural Conversational Flow and Structured Lead Nurturing | ✅ Pass — assistant handled a pricing question with clarifying questions instead of a flat answer, and stayed on-topic after an off-topic message |

No new maintained UAT scenarios exist yet for the Sprint 4 features shown live on July 12 (lead-discovery via group parsing, campaign analytics dashboard, manual dialog takeover). UAT-3 (lead discovery) and UAT-4 (analytics dashboard) have been added to `docs/user-acceptance-tests.md` for Sprint 5. Lead-discovery is logged as **Needs Improvement** rather than Pass, since Mark explicitly flagged its quality as a gap during live testing.

## Customer feedback → resulting issues

| Feedback | Resulting action |
|---|---|
| Lead-search/parsing quality needs improvement | New issue: improve lead-discovery/parsing result quality |
| Wants minimal-setup campaign start | New issue: reduce manual configuration to start a campaign |
| Bot occasionally breaks character | New issue: improve overall prompt/response quality, evaluate alternate LLM via existing routing API |
| Bot doesn't always merge rapid multi-message replies | New issue: merge chunked inbound messages more reliably |

## Follow-up for Sprint 5

The four items above have been created as GitHub issues and assigned to the Sprint 5 milestone.

## Handover status as of Week 6

- **Handover level reached: Ready for independent use.** The product runs on the production VPS, independent of any team member's local machine, and trial access has been shared directly with Mark. He has not yet used it independently or deployed it on his own side — that remains the Week 7 target.
- **Customer-confirmation status:** Positive verbal feedback received (off-record, same day) — Mark is satisfied overall, with two priorities: better prompt/response quality and stronger lead search. Written confirmation is still pending and will be collected before the Week 7 submission, as required evidence for Part 8.
