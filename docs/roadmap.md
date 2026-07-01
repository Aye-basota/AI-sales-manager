# Product Roadmap

## Product Goal

Build an autonomous B2B outbound sales assistant that uses real Telegram accounts and LLM-driven dialogue to generate qualified meetings with minimal human intervention.

---

## Previous Sprint

### Sprint 1 — MVP v1

**Goal:** Deliver a working sales funnel for automated Telegram outreach, from first contact to meeting booking.

**Dates:** 2026-06-09 – 2026-06-20

**Key Deliverables:**

- Configurable 4-stage sales funnel (hook → qualification → value → CTA)
- Funnel-aware LLM prompt generation
- Funnel stage tracking in `Conversation`
- Admin bot script creation with `first_message_goal` selection
- Analytics dashboard for replies, qualified leads, and meetings booked
- Multi-provider LLM support (OpenRouter + DashScope)

---

### Sprint 2 — Campaign Launch and Operational Readiness

**Goal:** Deliver a usable campaign-launch workflow for AI-powered outreach while improving product reliability and reducing implementation risks through validation, testing, and documentation improvements.

**Dates:** 2026-06-25 – 2026-07-09

**Sprint Focus:**

- Complete campaign-launch functionality
- Improve data import and campaign execution reliability
- Reduce operational risks
- Improve workflow readiness and documentation
- Maintain Sprint traceability and planning structure

---

## Current Sprint

### Sprint 3 — MVP v2: Production Deployment and AI Conversation Upgrade

**Goal:** Deliver MVP v2 by deploying the application to a production VPS for reliable 24/7 availability and enhancing the AI assistant with improved prompts, a more natural conversational flow, and a structured lead nurturing process that builds trust before guiding users through the sales funnel.

**Dates:** 2026-06-29 – 2026-07-04

**Sprint Focus:**

- Deploy application to production VPS for 24/7 availability
- Improve AI prompt quality for lead nurturing
- Implement natural multi-stage conversation flow
- Optimize sales funnel progression and user engagement
- Configure production infrastructure and monitoring
- Introduce prompt versioning and maintainability improvements

**Selected Sprint PBIs:**

- US-06: Increase lead turnover
- US-07: 24/7 availability
- US-017: Improve AI Prompt Quality for Lead Nurturing
- US-018: Implement Natural Multi-Stage Conversation Flow
- TECH-04: Implement sales script and funnel file upload API
- TECH-05: Build funnel preview endpoint and stage validation
- TECH-06: Track AI-automation rate per dialog session
- TECH-11: Deploy Application to Production VPS
- TECH-12: Configure Production Infrastructure and Monitoring
- TECH-13: Prompt Configuration and Versioning

**Sprint Scope Rationale:**

This Sprint focuses on delivering MVP v2 by deploying the application to a production VPS for reliable 24/7 availability and improving the AI assistant's conversational quality through enhanced prompts, a more natural dialogue flow, and an optimized lead-nurturing process.

The selected scope also includes production infrastructure improvements to increase system reliability, maintainability, and operational readiness while creating a more engaging user experience that supports higher-quality customer interactions and more effective sales conversion.

**Story Point Summary:**

- User stories: 23 SP
- Technical tasks: 12 SP
- **Sprint 3 total: 35 SP**

---

## Next Sprint

### Sprint 4 — Campaign Execution and Intelligence Layer

**Goal:** Enhance campaign execution capabilities and introduce deeper intelligence into lead management and analytics.

**Planned PBIs:**

- US-09: Manual Dialog Takeover
- US-010: Telegram Admin Bot for Management
- US-013: Monitor Active Dialogs in Real Time
- US-015: Campaign Analytics and Conversion Dashboard

**Planned Outcomes:**

- Better operator control over conversations
- Improved real-time monitoring of campaigns
- Stronger analytics and conversion tracking
- Enhanced operational visibility

---

## Future Directions

- Voice message support
- Image and media processing
- CRM integrations (HubSpot, Pipedrive)
- Calendar integrations (Google Calendar, Calendly)
- Advanced campaign analytics
- Real-time dashboards
- A/B testing for outreach campaigns
- Infrastructure scaling and performance optimization
