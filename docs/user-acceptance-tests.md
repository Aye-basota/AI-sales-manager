# User Acceptance Tests — AI Sales Manager

## UAT-001: Create Sales Script via Admin Bot

**Status:** Active  
**Priority:** Critical  
**Last Executed:** Week 4  
**Last Result:** Passed

**Scenario:**
1. Operator opens Admin Bot in Telegram.
2. Sends `/newscript` command.
3. Follows the step-by-step FSM flow to create a new sales script.
4. Enters script name, tone, and message templates.
5. Confirms script creation.
6. Verifies the new script appears in `/scripts` list.

**Expected Result:**
Script is created successfully and visible in the scripts list.

---

## UAT-002: Launch Campaign

**Status:** Active  
**Priority:** Critical  
**Last Executed:** Week 4  
**Last Result:** Passed

**Scenario:**
1. Operator opens Admin Bot.
2. Sends `/startcampaign` command.
3. Selects an existing script.
4. Selects target contacts.
5. Configures working hours and timezone.
6. Confirms campaign launch.
7. Verifies campaign status changes to "running" in `/campaigns` view.

**Expected Result:**
Campaign launches successfully and appears as "running" in the dashboard.

---

## UAT-003: Discover Leads via Telegram Search

**Status:** Active  
**Priority:** High  
**Last Executed:** Week 4  
**Last Result:** Passed

**Scenario:**
1. Operator opens Admin Bot.
2. Sends `/discover` command.
3. Enters a keyword for Telegram user search.
4. System returns a list of matching public users.
5. Operator can view found contacts with username and validity status.

**Expected Result:**
Lead discovery returns relevant Telegram users matching the search keyword.

---

## MVP v2 UAT Scenarios

## UAT-004: Upload and Preview Sales Funnel via API

**Status:** Active  
**Priority:** High  
**Last Executed:** —  
**Last Result:** —  
**Linked PBI:** [TECH-04](https://github.com/Aye-basota/AI-sales-manager/issues/24), [TECH-05](https://github.com/Aye-basota/AI-sales-manager/issues/25)

**Scenario:**
1. Operator opens the API docs at `/docs`.
2. Calls `POST /api/funnels/preview` with a valid JSON funnel definition containing stages `trust`, `engagement`, `qualification`, `value`, `cta`.
3. Verifies the response lists the stages with correct goals, instructions, and `allow_call_to_action` flags.
4. Calls `POST /api/funnels/upload` with the same funnel and an existing `campaign_id`.
5. Verifies the funnel is persisted and returned with HTTP 201.
6. Attempts to upload a funnel with a duplicate stage name and verifies HTTP 422.

**Expected Result:**
Funnel preview works without persistence; valid uploads are saved; invalid funnels are rejected with a clear error.

---

## UAT-005: View AI-Automation Rate and Escalation Status

**Status:** Active  
**Priority:** Medium  
**Last Executed:** —  
**Last Result:** —  
**Linked PBI:** [TECH-06](https://github.com/Aye-basota/AI-sales-manager/issues/26)

**Scenario:**
1. Operator runs a campaign and several dialogs complete without operator intervention.
2. Operator opens a conversation that required human intervention and updates its status via `PUT /conversations/{id}/status`.
3. Operator calls `GET /analytics/automation-rate`.
4. Verifies the response shows `total`, `ai_handled`, `escalated`, and `rate_pct`.
5. Confirms `escalated` equals the number of conversations with operator status changes and `rate_pct` reflects the AI-handled ratio.

**Expected Result:**
The automation-rate metric accurately distinguishes AI-handled dialogs from escalated dialogs.

---

## UAT-006: Verify Production Health Endpoint and Logs

**Status:** Active  
**Priority:** Medium  
**Last Executed:** —  
**Last Result:** —  
**Linked PBI:** [TECH-12](https://github.com/Aye-basota/AI-sales-manager/issues/54)

**Scenario:**
1. Operator deploys the product with `docker-compose up -d`.
2. Calls `GET /health` and verifies `status` is `ok`, `db` is `true`, and `scheduler` is `true`.
3. Checks container logs with `docker-compose logs api` and confirms structured log lines with timestamp, level, logger name, and message.
4. Stops PostgreSQL container and calls `GET /health` again.
5. Verifies the endpoint returns `status: degraded` and `db: false`.

**Expected Result:**
The health endpoint reports real system state, and logs are available in a consistent format for monitoring.

---

## UAT-007: Verify 24/7 Production Availability via VPS Deployment

**Status:** Active  
**Priority:** High  
**Last Executed:** —  
**Last Result:** —  
**Linked PBI:** TECH-11

**Scenario:**
1. Deploy the MVP v2 application to the production VPS.
2. Outside of standard business hours (e.g., at 3:00 AM), a user sends a message to the assistant via Telegram.
3. The system receives and processes the request.

**Expected Result:**
- The AI assistant replies with a relevant response within the defined latency threshold (< 3 seconds).
- No server timeouts, 502 Bad Gateway, or "application sleeping" errors occur.

---

## UAT-008: Verify Natural Conversational Flow and Structured Lead Nurturing

**Status:** Active  
**Priority:** High  
**Last Executed:** —  
**Last Result:** —  
**Linked PBI:** [US-017](https://github.com/Aye-basota/AI-sales-manager/issues/51), [US-018](https://github.com/Aye-basota/AI-sales-manager/issues/52)

**Scenario:**
1. A new, unrecognized user initiates a chat with the AI assistant.
2. The user asks top-of-funnel questions (e.g., asking for general information or expressing a common pain point).
3. The AI assistant responds using a natural, empathetic tone that directly addresses the user's specific question.

**Expected Result:**
- The assistant does NOT output a direct purchase link or aggressive sales call-to-action in its initial replies.
- Only after a predefined nurturing condition is met (e.g., 3 successful value-adding exchanges or the user explicitly asking for pricing/next steps) does the assistant smoothly transition the user into the structured sales funnel.
