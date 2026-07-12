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

## Current Sprint

### Sprint 4 — Trial Release Readiness and Production Stabilization

**Goal:** Enable a production-ready AI Sales Manager experience for the Week 6 trial release by delivering end-to-end lead management capabilities, including campaign execution, AI-driven conversations, analytics, and operational stability. The sprint aims to ensure the platform is ready for transition into real-world usage through a reliable user experience and stable production environment.

**Dates:** 2026-07-06 – 2026-07-12

**Sprint Focus:**

- Prepare the platform for the Week 6 trial release
- Strengthen end-to-end lead management workflows
- Improve campaign execution and contact handling reliability
- Enable manager involvement through manual dialog takeover and notifications
- Enhance analytics and visibility into campaign performance
- Improve AI automation tracking and prompt maintainability
- Ensure production deployment stability through infrastructure and monitoring improvements

**Selected Sprint PBIs:**

**User Stories**

- US-06: Increase Lead Turnover
- US-07: 24/7 Availability
- US-09: Manual Dialog Takeover
- US-015: Campaign Analytics and Conversion Dashboard
- US-019: Improve Admin Panel Navigation — Allow Editing After Campaign Launch Step

**Technical Tasks**

- TECH-03: Implement Manager Contact-Transfer Notification Flow
- TECH-06: Track AI-Automation Rate per Dialog Session
- TECH-08: CSV Contact Import — Persistence and Duplicate Handling
- TECH-11: Deploy Application to Production VPS
- TECH-12: Configure Production Infrastructure and Monitoring
- TECH-13: Prompt Configuration and Versioning

**Week 6 Trial Outcome:**

Sprint 4 reached a trial / handover-candidate state and was reviewed with the customer on 2026-07-12. The live review covered business setup, contact upload, campaign launch, AI conversation behavior, and Telegram lead discovery. The customer asked for stronger lead-search quality, less manual setup before campaign launch, and continued prompt/model quality improvement.

**Sprint Scope Rationale:**

The sprint scope focuses on strengthening the AI Sales Manager core workflow by addressing key product capabilities required for the Week 6 trial release and production readiness. The selected items improve the complete lead management journey — from campaign setup and contact handling to AI-powered conversations, manager involvement, performance analytics, and system reliability.

This scope ensures the platform can support real user trials by providing a stable production environment, improved operational visibility, and a reliable experience for both sales managers and end users. The sprint establishes the foundation required for a smooth transition from development into real-world usage.

**Story Point Summary:**

- User stories: 23 SP
- Technical tasks: 17 SP
- **Sprint 4 total: 40 SP**

---

## Planned Next Sprint

### Sprint 5 — Week 7 Follow-Up Maintenance and Final Handover

**Goal:** Use Week 6 trial feedback to remove the main transition blockers, confirm final product access, update handover documentation, and prepare the final course version (`MVP v3`) for customer and TA evaluation.

**Planned dates:** 2026-07-13 – 2026-07-19

**Planned Focus:**

- Create the Sprint 5 GitHub milestone and assign Week 6 follow-up issues to it.
- Confirm the final product access arrangement.
- Improve or explicitly scope lead-discovery result quality.
- Reduce campaign setup friction where feasible.
- Improve prompt/model behavior where Week 6 trial evidence showed role-breaking risk.
- Update customer-facing documentation and handover material after the final transition decision.
- Collect written customer confirmation for the reached handover level.

**Planned Outcomes:**

- Final `MVP v3` release candidate ready for SemVer release.
- Customer-facing documentation matches the actual transition state.
- Week 7 public report links the complete Week 6 evidence without duplicating it.
- Remaining limitations are explicit rather than hidden.
