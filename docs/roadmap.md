# Product Roadmap

## Product Goal

Build an autonomous B2B outbound sales assistant that uses real Telegram accounts and LLM-driven dialogue to generate qualified meetings with minimal human intervention.

## Roadmap Snapshot

The roadmap is reviewed after each Sprint Review and adjusted based on customer feedback, implementation risks, and release evidence.

| Milestone | Status | Target window | Focus | Release mapping |
|---|---|---|---|---|
| Sprint 1 — MVP v1 | Completed | 2026-06-09 to 2026-06-20 | End-to-end Telegram outreach funnel, funnel-aware prompts, admin script creation, analytics, and multi-provider LLM selection | `v0.1.0` |
| Sprint 2 — Hardening & Operator Tools | Planned | TBD | Reliability improvements and operator controls for live conversations | Next SemVer release |

## Completed Scope

Sprint 1 delivered the MVP v1 baseline:

- Configurable 4-stage sales funnel: hook → qualification → value → CTA.
- Funnel-aware LLM prompt generation.
- Funnel stage tracking in `Conversation`.
- Admin bot script creation with `first_message_goal` selection.
- Analytics for replies, qualified leads, and meetings booked.
- Multi-provider LLM support for OpenRouter and DashScope.

## Next Sprint Focus

Sprint 2 should harden the product around the live conversation flow:

- Inbound rate limiting and daily-limit guard per account.
- Redis distributed lock per `conversation_id` to prevent double replies.
- Operator manual takeover with an `is_paused_by_operator` flag.
- Funnel stage override in the admin bot and API.
- Funnel stage distribution in analytics.

## Longer-Term Directions

These items remain outside the immediate Sprint plan and should be revisited after the hardening work:

- Voice messages and photo support.
- Calendar integration for `meeting_intent` handoff.
- A/B testing for scripts.
- WebSocket real-time dashboard.
- External CRM integration such as HubSpot or Pipedrive.
