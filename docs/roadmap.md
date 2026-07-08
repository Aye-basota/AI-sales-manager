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

**Sprint Scope Rationale:**

The sprint scope focuses on strengthening the AI Sales Manager core workflow by addressing key product capabilities required for the Week 6 trial release and production readiness. The selected items improve the complete lead management journey — from campaign setup and contact handling to AI-powered conversations, manager involvement, performance analytics, and system reliability.

This scope ensures the platform can support real user trials by providing a stable production environment, improved operational visibility, and a reliable experience for both sales managers and end users. The sprint establishes the foundation required for a smooth transition from development into real-world usage.

**Story Point Summary:**

- User stories: 23 SP
- Technical tasks: 17 SP
- **Sprint 4 total: 40 SP**

---

## Next Sprint

### Sprint 5 — Post-Trial Optimization and Product Scaling

**Goal:** Improve the AI Sales Manager experience based on trial release feedback by optimizing AI performance, expanding analytics capabilities, and preparing the platform for broader adoption and increased campaign volume.

**Planned Focus:**

- Analyze trial release feedback and identify improvement areas
- Optimize AI conversation quality and lead qualification accuracy
- Improve campaign performance monitoring and reporting
- Enhance scalability and reliability for increased usage
- Expand automation capabilities and reduce manual intervention
- Improve user experience based on real-world usage patterns

**Planned Outcomes:**

- Higher-quality AI-driven customer conversations
- Improved lead conversion visibility and decision-making
- More scalable campaign execution
- Better operational efficiency for sales managers
- Increased platform readiness for wider adoptionng and performance optimization
