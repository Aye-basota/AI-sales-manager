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

### Sprint 3 — MVP v2: Production Deployment and AI Conversation Upgrade

**Goal:** Deliver MVP v2 by deploying the application to a production VPS for reliable 24/7 availability and enhancing the AI assistant with improved prompts, a more natural conversational flow, and a structured lead nurturing process that builds trust before guiding users through the sales funnel.

**Dates:** 2026-06-29 – 2026-07-04

**Sprint Achievements:**

- Deployed the application to a production VPS and established a stable environment for continuous availability
- Improved AI assistant behavior through enhanced prompt configuration and lead nurturing optimization
- Implemented a structured multi-stage conversation flow to guide leads through the sales funnel more naturally
- Improved sales funnel progression and user engagement through better AI-driven interactions
- Added production infrastructure monitoring to increase system reliability and operational visibility
- Introduced prompt versioning to support easier AI configuration management and future improvements

---

## Completed Sprint

### Sprint 4 — Trial Release Readiness and Production Stabilization

**Goal:** Deliver a production-ready AI Sales Manager for the Week 6 trial by completing end-to-end lead management capabilities, improving campaign execution, and ensuring stable production operation.

**Dates:** 2026-07-06 – 2026-07-12

**Sprint Achievements:**

- Improved campaign execution workflow and contact management reliability.
- Implemented manager notifications and manual conversation takeover for warm leads.
- Enhanced campaign visibility through lead information and notification improvements.
- Increased AI automation reliability and prompt maintainability.
- Strengthened CSV contact import with persistence and duplicate handling.
- Improved production deployment stability and infrastructure monitoring.
- Refined the admin panel workflow to simplify campaign management and editing.
- Successfully completed the Week 6 trial and collected customer feedback for the final quality improvements planned in Sprint 5.

---

## Final Current Sprint

### Sprint 5 — Final Quality Improvements and Production Transition

**Goal:** Finalize the quality improvements for lead discovery and AI interactions by delivering production-ready parsing accuracy and resilient prompt behavior, ensuring the system is stable and ready for final transition.

**Dates:** 2026-07-13 – 2026-07-19

**Selected Sprint PBIs:**

**User Stories**

- US-06: Increase Lead Turnover (5 SP)
- US-07: 24/7 Availability (5 SP)
- US-015: Campaign Analytics and Conversion Dashboard (5 SP)

**Technical Tasks**

- TECH-11: Deploy Application to Production VPS (5 SP)
- TECH-14: Improve Lead Discovery / Parsing Result Quality (3 SP)
- TECH-15: Improve Overall Prompt / Response Quality — Reduce LLM Role-Breaking (5 SP)

**Sprint Scope Rationale:**

This sprint focuses on completing the remaining quality improvements before the final transition. The team will finalize enhancements to lead discovery and parsing accuracy while reducing LLM role-breaking through prompt and response optimization. These activities improve the system's reliability, consistency, and readiness for final delivery without introducing significant new functionality.

**Expected Outcomes:**

- Improved lead discovery accuracy through enhanced parsing and filtering.
- More reliable AI conversations with reduced prompt failures and role-breaking.
- Stable production deployment supporting continuous 24/7 operation.
- Campaign notifications provide managers with warm lead information and contact details for timely follow-up.
- Product reaches a production-ready state suitable for final customer transition.

**Story Point Summary:**

- User stories: 15 SP
- Technical tasks: 13 SP
- **Sprint 5 total: 28 SP**
