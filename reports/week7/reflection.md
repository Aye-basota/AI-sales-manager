# Week 7 Reflection

This reflection is derived from repository analysis of the delta between the Week 6 trial release (`v0.4.0`) and the final Sprint 5 / `MVP v3` increment (`v0.5.0`), the Sprint 5 GitHub milestone, and `reports/week7/README.md`. It emphasizes follow-up maintenance, final transition work, customer usefulness, and the final delivery of `MVP v3`, per Assignment 6 Part 12.4.

---

## Learning points

- **Sprint 5 correctly scoped itself as maintenance, not new features.** At 28 Story Points across three user stories and three technical tasks (vs. Sprint 4's 40 SP), Sprint 5 matched Assignment 6 Part 6.2's allowance for a lighter, follow-up-focused Sprint. All six selected PBIs trace directly to Week 6 trial feedback or the unresolved VPS/access question, not to new product scope.

- **Follow-up maintenance targeted the exact gaps the customer raised.** `v0.5.0`'s changelog shows deliberate fixes to the three biggest Week 6 complaints: dialogue role-breaking (deterministic pricing/condition fallbacks, chat-formatted history instead of one flattened prompt, shorter role-consistent prompts), preview/send mismatch (approved Admin Bot preview text is now reused for the actual first send instead of being regenerated), and unsafe follow-up behavior (a single no-reply nudge with anti-repetition rules, and follow-ups now skipped after replies, operator intervention, or terminal states).

- **The access-artifact ambiguity from Week 6 was resolved by simplifying the story, not by finishing the VPS work.** Week 6's `docs/customer-handover.md` flagged an unresolved contradiction about whether the deployment was independent of a team member's machine. Week 7 resolves this pragmatically: the Telegram Admin Bot ([@salesmanager228_bot](https://t.me/salesmanager228_bot)) is now stated as the single final product access artifact, backed by a team-operated deployment — a inspectable, stable entry point for the customer and TA, even though the underlying "customer-owned VPS" work (`TECH-11`) is still open on GitHub.

- **Test and CI health improved substantially.** The suite grew from 708 tests (Week 6) to 991 tests at ~99% `app/` coverage, and the "Lint and type check" CI job — which was failing on `main` during Week 6 due to an unrelated pre-existing issue — is green again as of the current `main` commit.

- **Customer usefulness moved from "not yet reached" to a concrete, honestly-qualified status.** `docs/customer-handover.md` and `reports/week7/README.md` now state a reached handover level of `Ready for independent use` and a customer-confirmation status of `Accepted with follow-up items` — a real change from Week 6's "none of the three target levels reached," while still not overclaiming full `Accepted` status.

---

## Validated assumptions

- **Narrowly-scoped follow-up fixes are achievable in a single lighter Sprint.** Sprint 5 shipped `v0.5.0` with meaningful dialogue-quality and reliability fixes without expanding product scope, confirming Part 6.2's premise that a maintenance-focused Sprint is legitimate this late in the course.
- **A single, stable access artifact resolves handover ambiguity better than a partially-finished infrastructure item.** Naming the Telegram bot as the canonical `MVP v3` access path gave a concrete, testable claim instead of leaving the VPS question open and unresolved as in Week 6.
- **Reusing approved preview text for the actual send is a straightforward trust fix.** Storing the approved preview message on the queued contact (`app/models/campaign.py`, migration `20260715_campaign_contact_preview_message.py`) and reusing it at send time directly removes a "what you approved isn't what got sent" risk with minimal architectural change.

---

## Friction and gaps

- **Milestone-vs-delivered-work mismatch recurred from Week 6.** `reports/week6/retrospective.md`'s action points explicitly called for reconciling GitHub milestone state with shipped work. As of this report, the Sprint 5 milestone still shows 5 of 6 issues open (only `TECH-15`, prompt/response quality, is closed) even though `v0.5.0` ships real fixes for several of them. The same gap the team flagged after Sprint 4 was not fully closed in Sprint 5.
- **`TECH-11` (Production VPS) and `TECH-14` (lead-discovery/parsing quality) remain open.** The team's own Sprint 5 milestone selected both as in-scope; neither shipped. This should be explicitly re-scoped into declared post-course limitations rather than left as silently-abandoned open issues.
- **Customer-confirmation status is `Accepted with follow-up items`, not `Accepted`.** Written confirmation and the outstanding lead-discovery/deployment items are still pending per Assignment 6 Part 8's evidence requirements.
- **Several required Week 7 report artifacts were still outstanding when the Sprint 5 code/docs work landed.** `reports/week7/README.md` itself lists `reflection.md`, `retrospective.md`, `llm-report.md`, the Sprint Review summary/transcript, screenshots, and the public sanitized demo video as reserved for teammates — meaning Sprint 5's product delivery finished before all Assignment 6 Part 9–14 evidence did.

---

## Planned response

- Explicitly close, re-scope, or document as a declared post-course limitation: `TECH-11` (VPS/customer-owned deployment) and `TECH-14` (lead-discovery/parsing quality) — do not leave them open with no disposition at final submission.
- Collect and record written customer confirmation per Part 8, and update `docs/customer-handover.md` / `reports/week7/README.md` if the confirmation status changes as a result.
- Record and link the public sanitized demo video (Part 14) from both the `v0.5.0` release and `reports/week7/README.md`.
- Complete the remaining Week 7 report artifacts flagged as outstanding in `reports/week7/README.md` §5 (Sprint Review summary/transcript, retrospective, screenshots) before submission.
- Reconcile the Sprint 4 and Sprint 5 GitHub milestones with actually-delivered work, closing the gap the team identified but did not fully resolve after Sprint 4.
