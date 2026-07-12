# User Acceptance Tests

**Last updated:** 2026-07-12
**Sprint:** 4 (Week 6 trial release)

## Table of Contents
- [UAT 1: Verify 24/7 Production Availability via VPS Deployment](#uat-1-verify-247-production-availability-via-vps-deployment)
- [UAT 2: Verify Natural Conversational Flow and Structured Lead Nurturing](#uat-2-verify-natural-conversational-flow-and-structured-lead-nurturing)
- [UAT 3: Verify Lead-Discovery Result Quality via Telegram Group Parsing](#uat-3-verify-lead-discovery-result-quality-via-telegram-group-parsing)
- [UAT 4: Verify Campaign Analytics Dashboard Accuracy](#uat-4-verify-campaign-analytics-dashboard-accuracy)


## UAT 1: Verify 24/7 Production Availability via VPS Deployment

**Related PBIs / User Stories:**
- [US-07: 24/7 Availability](https://github.com/Aye-basota/AI-sales-manager/issues/9) (#9, Sprint 3)
- TECH-11: Deploy Application to Production VPS (#53, Sprint 3)
- TECH-12: Configure Production Infrastructure and Monitoring (#54, Sprint 3)

**Description:** Ensures the MVP v2 is successfully deployed to the production VPS and can reliably handle user interactions at any time, independently of a local development environment.

**Acceptance Criteria:**
- GIVEN the AI assistant application is fully deployed to the production VPS
- WHEN a user sends a message to the assistant via the messaging interface outside of standard business hours (e.g., at 3:00 AM)
- THEN the system should successfully receive and process the request
- AND the AI assistant should reply with a relevant response within the defined latency threshold (e.g., < 3 seconds)
- AND no server timeouts, 502 Bad Gateway, or "application sleeping" errors should occur

**Execution Result:**
- **Date executed:** 2026-07-05
- **Executed with:** Mark (customer)
- **Actual Result:** The customer selected a test company ("motor oils") and sent a message to the bot. The bot replied correctly and promptly, referencing the customer's business segment and relevant pain points. The customer then confirmed the local development machine and Docker environment were both fully shut down (approx. 10 PM at the time of the session) and sent a follow-up message asking the bot to elaborate on a product. The bot replied normally, confirming the assistant is served independently of any developer's local machine and remains available outside standard working hours.
- **Status:** ✅ Pass


## UAT 2: Verify Natural Conversational Flow and Structured Lead Nurturing

**Related PBIs / User Stories:**
- [US-018: Implement Natural Multi-Stage Conversation Flow](https://github.com/Aye-basota/AI-sales-manager/issues/52) (#52, Sprint 3)
- US-017: Improve AI Prompt Quality for Lead Nurturing (#51, Sprint 3)

**Description:** Ensures the enhanced system prompts successfully guide the AI to build trust through conversation rather than immediately pushing a hard sale or funnel link to the user.

**Acceptance Criteria:**
- GIVEN a new, unrecognized user initiates a chat with the AI assistant
- WHEN the user asks top-of-funnel questions (e.g., asking for general information or expressing a common pain point)
- THEN the AI assistant should respond using a natural, empathetic tone that directly addresses the user's specific question
- AND the assistant must NOT output a direct purchase link or aggressive sales call-to-action in its initial replies
- AND ONLY AFTER a predefined nurturing condition is met (e.g., 3 successful value-adding exchanges or the user explicitly asking for pricing/next steps)
- THEN the assistant should smoothly transition the user into the structured sales funnel
- AND, additionally to the sanity check performed under the older regression scenario, the assistant should not derail from off-topic messages and should steer the conversation back to the relevant subject

**Execution Result:**
- **Date executed:** 2026-07-05
- **Executed with:** Mark (customer)
- **Actual Result:** The customer asked a pricing-related question about maintenance/oil-change service. Instead of only returning a price, the assistant asked clarifying questions and guided the conversation toward booking, in a noticeably more natural, conversational tone compared to the previous version (which only returned a flat price). The customer also verified, as part of the older regression scenario, that an off-topic message was handled gracefully, with the assistant steering the conversation back on topic.
- **Status:** ✅ Pass


## UAT 3: Verify Lead-Discovery Result Quality via Telegram Group Parsing

**Related PBIs / User Stories:**
- Lead Discovery feature (see README — Telegram Search / Channel Parse / External API)

**Description:** Ensures lead-discovery via Telegram group parsing returns relevant, usable leads for a defined target audience, and that results are exportable in a campaign-compatible format.

**Acceptance Criteria:**
- GIVEN a business profile with a defined target audience
- WHEN the operator runs lead discovery with a related search query
- THEN the system should return contacts from thematically relevant Telegram groups
- AND results should be exportable to a campaign-compatible CSV
- AND result relevance should be sufficient for the operator to proceed without extensive manual filtering or repeated query attempts

**Execution Result:**
- **Date executed:** 2026-07-12
- **Executed with:** Mark (customer)
- **Actual Result:** An initial narrow query tied to the demo business context returned no results. After broadening the query, the search found relevant Telegram groups with matching thematic descriptions, and results exported correctly to a campaign-compatible CSV. Mark confirmed the export format and flow work, but flagged result coverage/relevance on the first attempt as a quality gap and named this his top priority for Sprint 5.
- **Status:** ⚠️ Needs Improvement

---

## UAT 4: Verify Campaign Analytics Dashboard Accuracy

**Related PBIs / User Stories:**
- US-015: Campaign Analytics & Conversion Dashboard

**Description:** Ensures the analytics dashboard accurately reflects live campaign metrics (reply rate, hot leads, automation rate) for operator decision-making, and only counts activity from running campaigns.

**Acceptance Criteria:**
- GIVEN a running campaign with sent messages and replies
- WHEN the operator opens the analytics dashboard
- THEN reply rate, hot-lead count, and automation rate should be displayed correctly
- AND metrics should reflect only running (not paused/closed) campaigns
- AND numbers should update as new messages/replies occur

**Execution Result:**
- **Date executed:** Not yet executed
- **Executed with:** —
- **Actual Result:** Not demoed live on the July 12 call. Recommend scheduling execution before Week 7 submission.
- **Status:** 🔲 Not yet executed

