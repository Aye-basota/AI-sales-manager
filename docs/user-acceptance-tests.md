# User Acceptance Tests

**Last updated:** 2026-07-12
**Sprint:** 4 (Week 6 trial / handover-candidate)

## Table of Contents

- [UAT 1: Verify 24/7 Production Availability via VPS Deployment](#uat-1-verify-247-production-availability-via-vps-deployment)
- [UAT 2: Verify Natural Conversational Flow and Structured Lead Nurturing](#uat-2-verify-natural-conversational-flow-and-structured-lead-nurturing)
- [UAT 3: Verify Lead-Discovery Result Quality via Telegram Group Parsing](#uat-3-verify-lead-discovery-result-quality-via-telegram-group-parsing)
- [UAT 4: Verify Campaign Analytics Dashboard Accuracy](#uat-4-verify-campaign-analytics-dashboard-accuracy)
- [UAT 5: Verify Minimal-Setup Campaign Launch](#uat-5-verify-minimal-setup-campaign-launch)

---

## UAT 1: Verify 24/7 Production Availability via VPS Deployment

**Stable ID:** UAT-001
**Scenario status:** Active

**Related PBIs / User Stories:**
- [US-07: 24/7 Availability](https://github.com/Aye-basota/AI-sales-manager/issues/9) (#9, Sprint 3)
- [TECH-11: Deploy Application to Production VPS](https://github.com/Aye-basota/AI-sales-manager/issues/53) (#53)
- [TECH-12: Configure Production Infrastructure and Monitoring](https://github.com/Aye-basota/AI-sales-manager/issues/54) (#54)

**Description:** Ensures the MVP v2 is successfully deployed to the production VPS and can reliably handle user interactions at any time, independently of a local development environment.

**Acceptance Criteria:**
- GIVEN the AI assistant application is fully deployed to the production VPS
- WHEN a user sends a message to the assistant via the messaging interface outside of standard business hours (e.g., at 3:00 AM)
- THEN the system should successfully receive and process the request
- AND the AI assistant should reply with a relevant response within the defined latency threshold (e.g., < 3 seconds)
- AND no server timeouts, 502 Bad Gateway, or "application sleeping" errors should occur

**Execution Result:**
- **Date executed:** 2026-07-05
- **Executed with:** customer/stakeholder
- **Actual Result:** The customer selected a test company ("motor oils") and sent a message to the bot. The bot replied correctly and promptly, referencing the customer's business segment and relevant pain points. The customer then confirmed the local development machine and Docker environment were both fully shut down (approx. 10 PM at the time of the session) and sent a follow-up message asking the bot to elaborate on a product. The bot replied normally, confirming the assistant is served independently of any developer's local machine and remains available outside standard working hours.
- **Status:** Pass

---

## UAT 2: Verify Natural Conversational Flow and Structured Lead Nurturing

**Stable ID:** UAT-002
**Scenario status:** Active

**Related PBIs / User Stories:**
- [US-018: Implement Natural Multi-Stage Conversation Flow](https://github.com/Aye-basota/AI-sales-manager/issues/52) (#52, Sprint 3)
- [US-017: Improve AI Prompt Quality for Lead Nurturing](https://github.com/Aye-basota/AI-sales-manager/issues/51) (#51, Sprint 3)

**Description:** Ensures the enhanced system prompts successfully guide the AI to build trust through conversation rather than immediately pushing a hard sale or funnel link to the user.

**Acceptance Criteria:**
- GIVEN a new, unrecognized user initiates a chat with the AI assistant
- WHEN the user asks top-of-funnel questions (e.g., asking for general information or expressing a common pain point)
- THEN the AI assistant should respond using a natural, empathetic tone that directly addresses the user's specific question
- AND the assistant must NOT output a direct purchase link or aggressive sales call-to-action in its initial replies
- AND ONLY AFTER a predefined nurturing condition is met (e.g., 3 successful value-adding exchanges or the user explicitly asking for pricing/next steps)
- THEN the assistant should smoothly transition the user into the structured sales funnel
- AND the assistant should not derail from off-topic messages and should steer the conversation back to the relevant subject

**Execution Result:**
- **Date executed:** 2026-07-05
- **Executed with:** customer/stakeholder
- **Actual Result:** The customer asked a pricing-related question about maintenance/oil-change service. Instead of only returning a price, the assistant asked clarifying questions and guided the conversation toward booking, in a noticeably more natural, conversational tone compared to the previous version. The customer also verified that an off-topic message was handled gracefully, with the assistant steering the conversation back on topic.
- **Status:** Pass

---

## UAT 3: Verify Lead-Discovery Result Quality via Telegram Group Parsing

**Stable ID:** UAT-003
**Scenario status:** Active

**Related PBIs / User Stories:**
- Explicit Sprint 5 transition action: improve Telegram lead-discovery/parsing result quality.
- Related existing pipeline issue: [TECH-08: CSV contact import persistence/duplicate handling](https://github.com/Aye-basota/AI-sales-manager/issues/28) (#28).

**Description:** Ensures lead discovery via Telegram group/message parsing returns relevant, usable leads for a defined target audience and exports them in a campaign-compatible CSV.

**Acceptance Criteria:**
- GIVEN a business profile with a defined target audience
- WHEN the operator runs lead discovery with a related search query
- THEN the system should return contacts from thematically relevant Telegram groups
- AND results should be exportable to a campaign-compatible CSV
- AND result relevance should be sufficient for the operator to proceed without extensive manual filtering or repeated query attempts

**Execution Result:**
- **Date executed:** 2026-07-12
- **Executed with:** customer/stakeholder
- **Actual Result:** An initial narrow query tied to the demo business context returned no results. After broadening the query, the search found relevant Telegram groups with matching thematic descriptions, and results exported correctly to a campaign-compatible CSV. The customer confirmed the export format and flow work, but flagged result coverage/relevance on the first attempt as a quality gap and named parsing/search quality as a top Sprint 5 priority.
- **Status:** Needs Improvement
- **Resulting PBIs / issues:** Explicit Sprint 5 transition action: tune lead-discovery query generation, filtering, and result-quality review; related import/export pipeline issue [#28](https://github.com/Aye-basota/AI-sales-manager/issues/28).

---

## UAT 4: Verify Campaign Analytics Dashboard Accuracy

**Stable ID:** UAT-004
**Scenario status:** Active

**Related PBIs / User Stories:**
- [US-015: Campaign Analytics and Conversion Dashboard](https://github.com/Aye-basota/AI-sales-manager/issues/20) (#20)
- [TECH-06: Track AI-automation rate per dialog session](https://github.com/Aye-basota/AI-sales-manager/issues/26) (#26)

**Description:** Ensures the analytics dashboard accurately reflects live campaign metrics such as reply rate, hot leads, and automation rate.

**Acceptance Criteria:**
- GIVEN a running campaign with sent messages and replies
- WHEN the operator opens the analytics dashboard
- THEN reply rate, hot-lead count, and automation rate should be displayed correctly
- AND metrics should reflect only running, not paused or closed, campaigns
- AND numbers should update as new messages/replies occur

**Execution Result:**
- **Date executed:** Not yet executed with the customer in Week 6
- **Executed with:** -
- **Actual Result:** Not demoed live on the July 12 call. The automated and local test evidence remains useful, but customer-executed analytics UAT should be scheduled during Week 7 if analytics is claimed as final transition-critical behavior.
- **Status:** Not yet executed

---

## UAT 5: Verify Minimal-Setup Campaign Launch

**Stable ID:** UAT-005
**Scenario status:** Active

**Related PBIs / User Stories:**
- Explicit Sprint 5 transition action: reduce manual configuration before campaign start.
- [US-019: Improve Admin Panel Navigation - Allow Editing After Campaign Launch Step](https://github.com/Aye-basota/AI-sales-manager/issues/68) (#68)

**Description:** Ensures the operator can describe a business, find or upload leads, review a reasonable first message, and launch a campaign without unnecessary repeated manual checks.

**Acceptance Criteria:**
- GIVEN Admin Bot is configured and reachable
- WHEN the operator creates/selects a business, adds contacts through upload or lead discovery, reviews the first message, and launches the campaign
- THEN the operator can complete the flow with minimal repeated setup
- AND the flow clearly shows the current step and allows correction before launch

**Execution Result:**
- **Date executed:** 2026-07-12
- **Executed with:** customer/stakeholder
- **Actual Result:** The end-to-end flow was demonstrated, but the customer asked for less manual configuration and a smoother launch path: after describing the business, the system should find relevant leads and be ready to launch with fewer approval/setup steps.
- **Status:** Needs Improvement
- **Resulting PBIs / issues:** [#68](https://github.com/Aye-basota/AI-sales-manager/issues/68) covers back/edit navigation; Sprint 5 should keep a setup-friction follow-up as an explicit transition action or dedicated issue.
