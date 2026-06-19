# Product Roadmap

## Product Goal

Build an autonomous B2B outbound sales assistant that uses real Telegram accounts and LLM-driven dialogue to generate qualified meetings with minimal human intervention.

## Current Sprint

### Sprint 1 — MVP v1

**Goal:** Deliver a working sales funnel for automated Telegram outreach, from first contact to meeting booking.

**Dates:** 2026-06-09 – 2026-06-20

**Key Deliverables:**

- Configurable 4-stage sales funnel (hook → qualification → value → CTA).
- Funnel-aware LLM prompt generation.
- Funnel stage tracking in `Conversation`.
- Admin bot script creation with `first_message_goal` selection.
- Analytics dashboard for replies, qualified leads, and meetings booked.
- Multi-provider LLM support (OpenRouter + DashScope).

## Next Sprint

### Sprint 2 — Hardening & Operator Tools

**Goal:** Improve reliability and give operators more control over live conversations.

**Planned PBIs:**

- Inbound rate limiting and daily-limit guard per account.
- Redis distributed lock per `conversation_id` to prevent double replies.
- Operator manual takeover with `is_paused_by_operator` flag.
- Funnel stage override in admin bot and API.
- Funnel stage distribution in analytics.

## Future Directions

- Voice messages and photo support.
- Calendar integration (Google Calendar / Calendly) for `meeting_intent`.
- A/B testing for scripts.
- WebSocket real-time dashboard.
- External CRM integration (HubSpot, Pipedrive).
