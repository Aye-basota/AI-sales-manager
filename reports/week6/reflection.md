# Week 6 Reflection

This reflection is derived from repository analysis and the delta between Sprint 3 (`v0.3.0`, MVP v2) and Sprint 4 (`v0.4.0`, Week 6 trial release), supplemented by the Sprint Review summary and customer trial on 2026-07-12. It emphasizes trial-release delivery, documentation review readiness, the customer meeting, and transition blockers identified for Week 7.

---

## Learning points

- **Sprint 4 shifted effort from configuration APIs to operator workflow.** Sprint 3 introduced external prompt config (`app/config/prompts/v1.json`), funnel upload/preview APIs, structured logging, and automation-rate analytics (ADR-005–008, QR-05–08). Sprint 4's diff shows the centre of gravity moved into `app/bots/admin_bot.py`, `app/bots/inbound_listener.py`, and `app/core/scheduler.py`, with supporting services such as `telegram_global_lead_search.py` and `initial_message_quality.py`. The product is no longer "API-first with a bot attached"; the Admin Bot is the primary trial surface.

- **Trial release hardening is a distinct increment from MVP v2.** `v0.4.0` changelog entries focus on startup resilience, inbound rate limiting, guardrail fixes, and API security (no `session_string` in responses) rather than new funnel stages. That pattern matches Assignment 6's Week 6 goal: a stable handover candidate, not a major feature milestone branded as MVP v3.

- **Lead discovery trade-off is visible in the architecture.** The team avoided TGStats API cost by parsing messages from groups the seller account already joins. The implementation is test-covered and demo-ready, but relevance depends on group membership and query quality — exactly the gap the customer flagged when asking to "finalize searches" before scaling outreach.

- **Handover documentation now states actual limits instead of marketing claims.** `docs/customer-handover.md` records that the repository, deployment, Telegram seller account, LLM keys, and Admin Bot token remain team-controlled; persistent hosting and recovery runbooks are missing. That honesty is necessary for Week 7 transition confirmation even though it exposes unfinished TECH-11/TECH-12 work.

- **Test volume grew faster than milestone hygiene.** Between tags, test files for Admin Bot, inbound listener, scheduler, and lead search expanded by thousands of lines, plus auxiliary scripts (`qa_audit.py`, `dialogue_lab.py`, `admin_ux_lab.py`). CI and local pytest give strong regression signal, but GitHub Sprint 4 issues stayed open, so process evidence and code evidence tell different stories.

- **Customer trial surfaced a deployment narrative conflict.** UAT-1 (2026-07-05) recorded Pass for VPS 24/7 availability, while the July 12 demo required a team laptop for access. Resolving that inconsistency is a Week 7 prerequisite for credible handover level reporting (`Ready for independent use` vs actual state).

---

## Validated assumptions

- **Issue-linked hardening PRs can ship a trial tag without closing every planned PBI** — `v0.4.0` was released from `main` with meaningful product changes while the Sprint 4 milestone still listed 40 SP of open work. Useful for deadline pressure; risky for course inspectability.
- **Group-based Telegram search is technically feasible without paid lead databases** — live demo found thematic contacts and exported CSV compatible with the existing contact-import path.
- **Rate limiting and humanizer delays are observable in customer demos** — typing behaviour and throttled outbound sends were demonstrated and understood; anti-spam measures are no longer invisible infrastructure.
- **Maintained handover and contributor docs integrate cleanly with existing `README.md` and hosted MkDocs site** — Assignment 6 Part 3–4 artefacts follow the same link graph as earlier `docs/` assets without duplicating setup steps from `LAUNCH_GUIDE.md`.

---

## Friction and gaps

- **Persistent product access artifact missing** — trial access still depends on team-operated Docker/localtunnel or a developer machine, blocking independent customer use and written handover acceptance.
- **LLM character stability** — guardrails block forbidden content but do not prevent occasional out-of-role replies; customer tied this to model selection, not only prompt text.
- **Campaign setup still multi-step** — business definition, contact upload, first-message approval, and launch remain separate; customer wants a compressed "describe → find → send" path.
- **UAT registry lag** — Sprint 4 demo features lack maintained UAT scenarios and execution history; Week 6 public report cannot yet trace trial feedback to formal UAT IDs for lead discovery or analytics.
- **Sprint board vs release traceability** — milestone, release notes, and codebase describe different "done" boundaries; graders reviewing GitHub Projects alone will underestimate delivered work or overestimate Sprint completion.

---

## Planned response

- Sprint 5 (Week 7) should prioritize TECH-11/TECH-12 and customer-independent access before new feature breadth, then address trial feedback: parsing quality, LLM model evaluation, and reduced campaign-setup steps (see Sprint Review follow-up table in [`sprint-review-summary.md`](./sprint-review-summary.md)).
- Add UAT-3/UAT-4 (or equivalent) for lead discovery and analytics; re-execute UAT-1 against the actual Week 7 hosting arrangement.
- Update `docs/customer-handover.md` and `reports/week7/README.md` with reached handover level and customer-confirmation status once VPS or an agreed access model is in place.
- Close or re-scope open Sprint 4 milestone issues so MVP v3 release traceability matches GitHub state.
