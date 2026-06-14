# Week 2 Analysis — AI Sales Manager

## Learning Points

### User Stories & Prioritization
- Writing user stories in the standard "As a… I want… so that…" format forces clarity on who benefits and why. Several initial stories were rewritten when we realized the goal was vague.
- MoSCoW prioritization revealed that 9 of 15 stories are Must Have — the MVP scope is still large. We need stricter trimming for MVP v1.
- Separating requirement status (Active/Removed) from priority (Must/Should/Could/Won't Have) helped us keep removed stories documented without distorting the priority list.

### Prototyping & Interface Design
- The product has two distinct interfaces: a web UI (primary) and a Telegram bot (secondary). Designing both clarified that the web UI must handle complex management tasks while the bot should focus on lightweight monitoring.
- Mocking the contact import flow exposed ambiguity in the CSV format — we defined required columns (name, telegram_id, position, company) as a result.
- The AI Manager creation form requires careful UX: describing a persona in text is abstract, so placeholder examples and tooltips will be critical.

### MVP v0 Deployment
- The existing backend (FastAPI + Telegram bot) provides a foundation: CSV upload and bot notification endpoints exist from the previous project.
- Docker setup is already in place, which simplifies reproducible deployment.
- MVP v0 can reuse the CSV upload API and Telegram bot infrastructure, but the AI Manager logic, task scheduler, and dialog storage need to be built from scratch.

### Customer Validation
- From Assignment 1 interview, the customer confirmed: Telegram-first, working hours 09:00–18:00 MSK, and anti-spam intervals are non-negotiable.
- The customer expects human-like dialogue quality — this is a technical risk that needs early LLM testing.

---

## Validated Assumptions

| Assumption | Validation | Source |
|-----------|-----------|--------|
| Customer prefers Telegram over WhatsApp for MVP | Confirmed — customer explicitly stated Telegram is priority | Interview (Assignment 1) |
| Working hours must be configurable, not 24/7 | Confirmed — customer requires 09:00–18:00 MSK with timezone awareness | Interview |
| Anti-spam: one initial message + follow-up after N hours | Confirmed — customer described exact pattern | Interview |
| CSV/Excel is the primary contact import format | Confirmed — customer mentioned uploading lead bases | Interview |
| Sales director is the primary user, not a technical person | Confirmed — interface must be simple, no CLI or API knowledge needed | Interview |
| Multiple scripts needed (3–5) for different products | Confirmed — customer has B2B and B2C products requiring different approaches | Interview |
| LLM provider should be swappable | Confirmed — customer prefers Qwen but wants testing of Gemini and DeepSeek | Interview |
| Contact parsing is the hardest technical challenge | Rejected — the customer confirmed this is a key differentiator but not an MVP blocker; manual CSV import is acceptable for MVP | Interview |

---

## Needs Clarification

1. **Telegram Bot API vs User API**: The official Bot API cannot initiate conversations with users who haven't first messaged the bot. Cold outreach requires the User API (Telegram client library), which risks account bans. We need customer approval to proceed with the riskier approach or find a workaround.

2. **Opt-in / Consent Base**: Does the customer have a pre-existing contact base with consent for cold messaging? If not, how do we handle compliance?

3. **Qualification Criteria Definition**: What exactly constitutes "warm" vs "hot"? The customer mentioned "bringing to a call," but intermediate signals (price request, presentation agreement, etc.) need definition.

4. **WhatsApp Priority for V2**: Explicit confirmation needed that WhatsApp is acceptable for post-MVP.

5. **LLM API Keys**: The customer will provide API keys — confirm timeline for this so we can start testing Qwen vs alternatives.

6. **Human Takeover Scope**: In Assignment 1, the customer agreed read-only chat + manual status change is enough for MVP. Confirm this still holds.

7. **Notification Channel**: How does the customer want qualified-lead notifications — Telegram bot, email, or in-app?

8. **Timezone Handling**: Should working hours be in the contact's timezone or a fixed timezone (MSK)?

---

## Planned Response

1. **Stricter MVP scope trimming**: Move US-06 (dialog list) and US-08 (funnel reports) to Should Have for MVP v1 if development time is insufficient. Focus engineering on the core loop: import → AI manager → task → dialog.

2. **Prototype first, build second**: Complete the Figma prototype for all MVP v1 screens before starting frontend implementation. This will surface UX issues early.

3. **LLM early spike**: Dedicate one team member to test Qwen, Gemini, and DeepSeek on a sample sales script in Week 3 to de-risk dialogue quality before full integration.

4. **Contact parsing as V2 differentiator**: Focus MVP v0/v1 on CSV import only. Parsing (US-09) can be the key V2 feature that differentiates from competitors.

5. **Telegram API risk assessment**: Evaluate pyrofork/Telethon for User API approach in Week 3. If risk is too high, propose a workaround (e.g., bot sends invitation links, leads click to start conversation).

6. **Customer follow-up**: Schedule a clarification meeting in Week 3 to resolve open questions (API approach, consent base, qualification criteria) before MVP v1 implementation begins.
