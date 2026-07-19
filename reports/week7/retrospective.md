# Sprint 5 Retrospective (Assignment 6 — Week 7)

**Sprint:** Sprint 5 — Post-Trial Optimization and Final Transition (`MVP v3`)  
**Dates:** 2026-07-13 – 2026-07-19  
**Sprint Goal:** Finalize quality improvements for lead discovery and AI interactions by delivering production-ready parsing accuracy and resilient prompt behavior, ensuring the system is stable and ready for final transition.  
**Facilitator:** Scrum Master  
**Participants:** Development Team, Product Owner (customer representative)

---

## What went well

1. **Sprint 5 stayed maintenance-focused and shipped `MVP v3` candidate work** — PR [#96](https://github.com/Aye-basota/AI-sales-manager/pull/96) delivered follow-up dialogue fixes, preview/send consistency, follow-up safety gates, release metadata `0.5.0`, and an updated Week 7 index without expanding into a new feature milestone. That matches Assignment 6 Part 6's allowance for a lighter follow-up Sprint.
2. **Week 6 customer feedback mapped to concrete product changes** — role-breaking risk was reduced with shorter prompts, chat-formatted history, and deterministic pricing/condition fallbacks (`TECH-15` closed); approved Admin Bot preview text is reused for the first send; follow-ups are limited to a single no-reply nudge and skipped after replies, operator intervention, escalations, or terminal states.
3. **Final handover status became inspectable** — `docs/customer-handover.md` and `reports/week7/README.md` now state a reached handover level of `Independently used by customer` and customer-confirmation status of `Accepted with follow-up items`, with [@salesmanager228_bot](https://t.me/salesmanager228_bot) as the final product access artifact.
4. **Regression evidence improved with the maintenance scope** — Sprint 5 added/updated tests for follow-up quality, scheduler eligibility, inbound prompts, guardrails, business-owner clarification, and humanizer chunking while keeping Assignment 4/5 CI gates active.
5. **Maintained docs stayed current with the product change** — architecture notes (`docs/architecture/README.md`, ADR-003), testing status, roadmap Sprint 5 section, UAT updates, and customer-facing handover text were updated alongside the code rather than deferred entirely to report week.

---

## What did not go well

1. **GitHub milestone hygiene still lagged delivered work** — several Sprint 5 milestone issues remain open on GitHub while labels / PR #96 claim Done for overlapping scope (for example TECH-11, US-06, US-07, US-015, TECH-14). Inspectors reading only the milestone board still cannot trust issue state as the delivery source of truth.
2. **Customer-owned VPS / hosting story was reframed rather than fully completed** — Week 6 action points treated TECH-11/TECH-12 as a hard gate. Sprint 5 resolved the access ambiguity by naming the team-operated Telegram bot as the course evaluation artifact and documenting Docker self-hosting, but customer-owned persistent infrastructure transfer remains a follow-up item rather than a finished stronger handover level.
3. **GitHub issue state lagged customer-confirmed product state** — the customer confirmed lead-discovery quality improved enough for Week 7, but `TECH-14` and several other Sprint 5 milestone items still need manual GitHub reconciliation so the board does not imply unfinished Must Haves without disposition.
4. **Final packaging artefacts trailed product delivery** — when the Sprint 5 maintenance PR landed, the Week 7 report still reserved screenshots and the public sanitized demo video for later teammates. Product readiness outpaced Assignment 6 Parts 13–14 evidence completion.
5. **`v0.5.0` GitHub Release was not yet published at retrospective time** — `CHANGELOG.md` and API metadata already identify `0.5.0` / `MVP v3`, but the SemVer tag/release packaging required by Assignment 6 Part 7 still needs to be created on protected `main` after the final fixes PR is merged.

---

## What the team changed or attempted to change based on the previous Sprint Retrospective, and what results they observed

The [Sprint 4 retrospective](../week6/retrospective.md) listed two action points. Sprint 5 response:

| Previous action point | Sprint 5 response |
|---|---|
| Close the VPS / hosting blocker before Sprint 5 feature work; update `docs/customer-handover.md` with the real product access artifact URL; treat persistent hosting as a gate for MVP v3 and written customer confirmation. | **Partially achieved.** The final access artifact is now explicit ([@salesmanager228_bot](https://t.me/salesmanager228_bot)), handover level is `Independently used by customer`, and confirmation is `Accepted with follow-up items`. Full customer-owned VPS transfer / stronger handover levels were not reached; hosting remains team-operated for course evaluation with documented self-hosting as the independence path. |
| Reconcile GitHub milestone state with shipped increments; avoid releasing another SemVer tag while milestone issues remain open. | **Not fully achieved.** Sprint 5 closed some related work via PR #96 (notably `TECH-15`) and marked several stories Done in labels/`docs/user-stories.md`, but open-issue counts on the Sprint 5 milestone still diverge from the shipped `0.5.0` increment. The formal `v0.5.0` GitHub Release is still pending, which at least avoided publishing a mapped release against a fully stale open board — but board/release hygiene remains incomplete. |

Additional changes compared to Sprint 4:

| Area | Sprint 4 (`v0.4.0`, trial) | Sprint 5 (`0.5.0`, `MVP v3` candidate) |
|---|---|---|
| Primary focus | Trial release hardening, Admin Bot operator path, lead discovery demo | Follow-up maintenance: dialogue correctness, follow-up safety, preview/send consistency |
| Customer feedback posture | Collected live; converted to planned Sprint 5 issues | Executed highest-risk dialogue/follow-up fixes; lead-search quality confirmed improved by customer, GitHub issue state still needs reconciliation |
| Handover claim | No formal handover level reached | `Independently used by customer` + `Accepted with follow-up items` |
| Access artifact | Ambiguous VPS vs laptop contradiction | Canonical Telegram bot access path documented |
| Test signal | Large Week 6 expansion (~708 tests) | Further regression growth beyond 1,000 tests, with late mock/lint cleanup required after final product changes |
| Course artefacts | Week 6 report largely filled late | Week 7 index, Sprint Review summary/transcript, retrospective, reflection, and LLM report exist; release/video/screenshots remain external packaging actions |

---

## Action points

1. **Publish and link the final `v0.5.0` SemVer release on protected `main`** — include Sprint 5 milestone, bot access, `docs/customer-handover.md`, `reports/week7/README.md`, and the public sanitized demo video (Part 14) before Week 7 Moodle submission.
2. **Close, re-scope, or explicitly declare post-course limitations for remaining open Sprint 5 items** — especially `TECH-14` (lead-discovery quality), reporting tasks, and any still-open hosting/transfer work — so the milestone board matches the final claimed handover level instead of implying unfinished Must Haves without disposition.
