# User Acceptance Tests (UAT)

This document contains end-user-facing scenarios that the customer or stakeholder can execute to verify that the product supports intended user goals.

## UAT-001: Launch a Campaign

- **Status:** Active
- **User goal:** A sales director can create a script, import contacts, and launch a campaign.
- **Preconditions:** Telegram seller account is configured; contacts are available.
- **Steps:**
  1. Create a sales script via Admin Bot (`/newscript`) or API.
  2. Import contacts via `/upload` or `POST /contacts/import`.
  3. Create and start a campaign.
  4. Verify that messages are sent according to working hours and rate limits.
- **Expected outcome:** Campaign status is `running`; initial messages are delivered to contacts.

## UAT-002: Handle a Positive Reply

- **Status:** Active
- **User goal:** The system detects a positive reply and escalates the lead.
- **Preconditions:** A campaign is running and a contact has received an initial message.
- **Steps:**
  1. Contact replies with a positive message.
  2. System classifies intent and generates an answer.
  3. Operator receives a hot-lead alert.
- **Expected outcome:** Conversation state moves to `hot`; operator notification is sent.

## UAT-003: Pause and Resume a Campaign

- **Status:** Active
- **User goal:** An operator can pause a running campaign and resume it later.
- **Preconditions:** A campaign is running.
- **Steps:**
  1. Use Admin Bot `/campaigns` or API to pause the campaign.
  2. Verify no new messages are sent.
  3. Resume the campaign.
- **Expected outcome:** Campaign status changes to `paused` and back to `running`.

## MVP v2 UAT Scenarios

Add at least two new scenarios here for functionality delivered in `MVP v2`.

### UAT-004: *(fill in for MVP v2 feature)*

- **Status:** Active
- **User goal:** *(fill in)*
- **Preconditions:** *(fill in)*
- **Steps:**
  1. *(fill in)*
- **Expected outcome:** *(fill in)*

### UAT-005: *(fill in for MVP v2 feature)*

- **Status:** Active
- **User goal:** *(fill in)*
- **Preconditions:** *(fill in)*
- **Steps:**
  1. *(fill in)*
- **Expected outcome:** *(fill in)*
