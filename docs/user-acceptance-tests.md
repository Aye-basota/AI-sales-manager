# User Acceptance Tests (UAT)

Project: AI Sales Manager

---

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

Add at least two new scenarios here for functionality delivered in `MVP v2`.

## UAT-004: *(fill in for MVP v2 feature)*

**Status:** Active
**Priority:** *(fill in)*
**Last Executed:** —
**Last Result:** —

**Scenario:**
1. *(fill in)*

**Expected Result:**
*(fill in)*

---

## UAT-005: *(fill in for MVP v2 feature)*

**Status:** Active
**Priority:** *(fill in)*
**Last Executed:** —
**Last Result:** —

**Scenario:**
1. *(fill in)*

**Expected Result:**
*(fill in)*
