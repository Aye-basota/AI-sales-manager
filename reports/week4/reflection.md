# Week 4 Reflection — AI Sales Manager

## Learning points

### Responding to Customer Feedback
- Translating customer feedback into actionable PBIs requires prioritization discipline. The customer raised five points after the MVP v1 demo; only three could be addressed in this Sprint. Deferring items explicitly (with a linked backlog issue and a written reason) is better than silently ignoring them.
- Feedback on "robotic feel" was the hardest to translate into a measurable acceptance criterion. We eventually tied it to humanizer configuration — typing speed range and thinking delay bounds — which made it testable.
- The customer confirmed that hot-lead alerts via the Admin Bot satisfied their core notification requirement. This validated our decision to use the Telegram bot as the operator interface rather than building a separate web dashboard.

### Defining Quality Requirements
- Writing quality requirements in the ISO/IEC 25010 scenario format (stimulus → response → measurable outcome) forces precision. Our first drafts were vague ("the system should be fast"); the scenario format forced us to name a specific trigger, a specific system response, and a specific measurable result.
- Selecting different ISO/IEC sub-characteristics for each requirement revealed gaps: we initially had three security-flavoured requirements and no reliability or usability requirements. Reviewing the sub-characteristic taxonomy prompted us to add the state machine correctness (fault tolerance) and anti-repetition (user error protection) requirements.

### Automating Quality Requirement Tests
- The state machine and guardrails were easy to automate because they are pure functions with no side effects. Scheduler tests were harder — they required `AsyncMock` for DB and Pyrogram, and the timezone-aware filtering logic had subtle edge cases near midnight.
- Linking QRT files from `docs/quality-requirement-tests.md` made it clear that some quality requirements were covered by multiple existing tests. We consolidated these rather than writing duplicate tests.

### CI and Coverage
- Setting a per-module coverage threshold (≥ 30%) highlighted that `app/api/` endpoints had lower coverage than expected. Most API tests use `TestClient` but do not test database error paths.
- Adding Bandit as an additional QA check caught one legitimate issue: a `subprocess` call in `scripts/generate_session.py` that was not marked as reviewed. This was suppressed with `# nosec` after manual review, which is the correct process.

---

## Validated assumptions

| Assumption | Outcome | Evidence |
|---|---|---|
| Telegram MTProto outreach satisfies customer requirements better than Bot API | Confirmed — customer explicitly validated that messages arriving from real accounts feel authentic | Sprint Review discussion |
| LLM fallback cascade (Qwen → Gemini → DeepSeek) is reliable enough for MVP | Partially confirmed — cascade works under test, but DashScope rate limits caused one real campaign failure. Fallback to hardcoded message fired correctly | Production log (Admin Bot alert) |
| State machine as a pure function is the right abstraction | Confirmed — 100% test coverage, zero production bugs related to state transitions so far | CI coverage report |
| Working hours timezone filter is sufficient to prevent off-hours messages | Confirmed in testing; one edge case found at DST boundary (Europe/Moscow is UTC+3, no DST, so this is not a real risk for the current target market) | `tests/test_timezone.py` |
| CSV/Excel import covers customer's contact sourcing workflow | Confirmed — customer used Excel import successfully during UAT; did not request Telegram channel parsing for MVP | UAT session |

---

## Friction and gaps

### Technical Gaps

1. **Race condition on rapid inbound messages** — two messages arriving within 1 second can produce two LLM responses. A Redis distributed lock on `conversation_id` is the fix but was not implemented this Sprint. Risk is low for B2B (leads rarely send rapid-fire messages), but it is a known issue.

2. **Inbound flood bypass of daily limit** — if a lead sends 10 messages in sequence, the bot replies to all, potentially exceeding the account's `daily_messages_sent` limit. Fix is ~5 lines, deferred to next Sprint.

3. **`processed_contacts` metric is misleading** — the counter increments per message sent, not per unique contact. A campaign with 5 contacts that sends initial + follow-up shows "10 processed" instead of "5 processed". This confuses the sales director reading the dashboard.

4. **No API authentication** — FastAPI endpoints have no auth layer. Acceptable for a single-tenant internal deployment, but must be addressed before any multi-tenant or internet-exposed deployment.

5. **LLM prompt quality is not automatically tested** — guardrails catch structural problems, but dialogue quality (relevance, tone, persuasiveness) is only validated manually during Sprint Reviews. No automated quality metric exists for this yet.

### Process Gaps

1. **Reviewer availability** — one Sprint PBI waited 2 days for a reviewer because the assigned reviewer was blocked on another task. We need a backup reviewer rule in the Definition of Done.

2. **Missing rollback procedure** — no documented procedure for rolling back a bad deployment. Docker Compose makes this easy in practice (image tag rollback), but it is not written down.

3. **UAT scenario coverage** — three UAT scenarios were executed but two of them tested the same flow (campaign creation → message send). Next Sprint should add a UAT scenario specifically for the inbound reply and hot-lead alert flow.

---

## Planned response

| Gap | Action | Linked PBI/Issue |
|---|---|---|
| Race condition on rapid inbound messages | Add Redis distributed lock on `conversation_id` in `InboundListener` | Backlog — create issue before Sprint 5 |
| Inbound flood bypass | Add `daily_messages_sent` check before inbound reply in `InboundListener.handle_message()` | Backlog — create issue before Sprint 5 |
| `processed_contacts` metric bug | Fix counter to increment per unique contact, not per message | Backlog |
| API authentication | Add JWT or API-key middleware to FastAPI | Roadmap — P1 for multi-tenant readiness |
| Backup reviewer rule | Update `docs/definition-of-done.md` to require a named backup reviewer | Definition of Done update — this Sprint retrospective action |
| Rollback procedure | Add rollback section to `LAUNCH_GUIDE.md` | Documentation PBI — Sprint 5 |
| UAT coverage gap | Add UAT scenario for inbound reply → hot-lead alert flow | `docs/user-acceptance-tests.md` update |
