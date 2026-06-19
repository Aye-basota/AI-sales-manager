# Customer Review Summary

## Meeting Details

- **Date:** 2026-06-19
- **Participants:** Sales Director (Customer), Product Owner, Tech Lead
- **Artifacts demonstrated:**
  - MVP v1 sales funnel (hook → qualification → value → CTA)
  - Admin Bot script creation flow
  - Analytics dashboard
  - LLM provider switch (OpenRouter / DashScope)

## Scope Reviewed

The team demonstrated the MVP v1 scope agreed in Assignment 2:

- Product information delivery through LLM-generated messages.
- Contact/escalation path to a human owner.
- Bot setup and funnel upload via API and Admin Bot.
- Labor-cost reduction through autonomous reply handling.
- LLM provider selection for cost/quality balancing.

## Customer Feedback

- **Positive:** The funnel approach matches the customer's sales process.
- **Positive:** Admin Bot makes it easy to create scripts without opening a web UI.
- **Request:** Add manual operator takeover for hot leads.
- **Request:** Show funnel stage distribution in analytics.
- **Request:** Add inbound rate limiting to protect Telegram accounts.

## Approvals and Changes

- Customer **approved** MVP v1 increment as a working foundation.
- Requested changes were added to the Product Backlog for Sprint 2:
  - Operator takeover (US-09)
  - Funnel stage analytics (new PBI)
  - Inbound rate limiting (new PBI)

## Action Points

1. Create Sprint 2 milestone and add the three new PBIs.
2. Prioritize operator takeover as the first Sprint 2 item.
3. Schedule follow-up review after Sprint 2 completion.

## Risks

- Telegram account limits may require more conservative rate settings.
- Operator takeover must prevent bot-human message collisions.
