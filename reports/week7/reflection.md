# Week 7 Reflection

This reflection is derived from repository analysis of the delta between the Week 6 trial release (`v0.4.0`) and the final Sprint 5 / `MVP v3` increment (`0.5.0`), the Sprint 5 GitHub milestone, PR [#96](https://github.com/Aye-basota/AI-sales-manager/pull/96), and `reports/week7/README.md`. It emphasizes follow-up maintenance, final transition work, customer usefulness feedback, and final delivery of `MVP v3`, per Assignment 6 Part 12.4.

---

## Learning points

- **Sprint 5 correctly scoped itself as maintenance, not new features.** At 28 Story Points across three user stories and three technical tasks (vs. Sprint 4's 40 SP), Sprint 5 matched Assignment 6 Part 6.2's allowance for a lighter, follow-up-focused Sprint. Selected PBIs traced to Week 6 trial feedback or the unresolved access question, not to speculative new product scope.

- **Follow-up maintenance targeted the exact gaps the customer raised.** The `0.5.0` changelog shows deliberate fixes to the highest-risk Week 6 complaints: dialogue role-breaking (deterministic pricing/condition fallbacks, chat-formatted history, shorter role-consistent prompts), preview/send mismatch (approved Admin Bot preview text reused for the actual first send), and unsafe follow-up behavior (single no-reply nudge with anti-repetition rules; follow-ups skipped after replies, operator intervention, or terminal states).

- **The access-artifact ambiguity from Week 6 was resolved by simplifying the public claim.** Week 6's handover notes flagged an unresolved contradiction about whether the deployment was independent of a team member's machine. Week 7 names the Telegram Admin Bot ([@salesmanager228_bot](https://t.me/salesmanager228_bot)) as the final course access artifact, backed by a team-operated deployment plus reproducible Docker self-hosting — inspectable for customer/TA evaluation without overclaiming customer-owned VPS transfer.

- **Test and CI health tracked the maintenance work, but final packaging still required one cleanup pass.** The suite grew beyond 1,000 tests with new regression coverage around follow-up quality, scheduler eligibility, inbound prompts, and humanizer chunking. The final audit found stale mocks and one lint issue after a late scheduler/business-clarification merge, which were addressed before final packaging.

- **Customer usefulness moved from "not yet reached" to an honestly qualified status.** `docs/customer-handover.md` and `reports/week7/README.md` now state handover level `Independently used by customer` and customer-confirmation status `Accepted with follow-up items` — a real change from Week 6's trial-only state, while still not overclaiming customer-side deployment.

---

## Validated assumptions

- **Narrowly scoped follow-up fixes are achievable in a single lighter Sprint.** Sprint 5 prepared the final `MVP v3` increment with meaningful dialogue-quality and reliability fixes without expanding product breadth, confirming Part 6.2's premise that a maintenance-focused Sprint is legitimate this late in the course.
- **A single stable access artifact resolves handover ambiguity better than an unfinished infrastructure claim.** Naming the Telegram bot as the canonical `MVP v3` access path produced a concrete, testable public statement instead of leaving the VPS question open and contradictory.
- **Reusing approved preview text for the actual send is a high-trust, low-architecture fix.** Storing approved preview text on the queued contact and reusing it at send time removes a "what you approved isn't what got sent" failure mode with a focused migration and Admin Bot/scheduler change.

---

## Friction and gaps

- **Milestone-vs-delivered-work mismatch recurred from Week 6.** Sprint 4's retrospective already called for reconciling GitHub milestone state with shipped work. Sprint 5 closed `TECH-15` and marked several items Done in docs/labels, but multiple Sprint 5 milestone issues remain open while `0.5.0` product changes are already on `main`.
- **GitHub milestone state still needs manual reconciliation.** The customer confirmed lead-discovery quality as resolved, but issue [#90](https://github.com/Aye-basota/AI-sales-manager/issues/90) and other Sprint 5 milestone items still need to be closed, re-scoped, or explicitly left as post-course follow-up in GitHub.
- **Final SemVer packaging and Demo Day artefacts require external action.** `CHANGELOG.md` and API metadata identify `0.5.0` / `MVP v3`, but the actual GitHub Release, public sanitized demo video, screenshots, slide deck, rehearsal video, and Moodle PDFs require team-owned accounts and private evidence channels.
- **Customer-confirmation status is `Accepted with follow-up items`, not unconditional `Accepted`.** Documentation clarity, UAT-005 re-test, and optional customer-owned hosting must stay visible in the public handover docs and private Moodle evidence rather than being silently dropped.

---

## Planned response

- Publish the final `v0.5.0` SemVer release on protected `main` and link it from `reports/week7/README.md`, including the public sanitized demo video once Part 14 is ready.
- Close, re-scope, or explicitly declare post-course limitations for remaining open Sprint 5 items — especially lead-discovery quality, Sprint 5 reporting tasks, and customer-owned infrastructure transfer — so the milestone board matches the claimed handover level.
- Keep private Week 7 confirmation evidence (written acceptance / follow-up list, recording timecodes, access instructions) aligned with the public statements in `docs/customer-handover.md`.
- Add Week 7 screenshots and Demo Day preparation evidence before Moodle submission.
