# Sprint 4 Retrospective (Assignment 6 — Week 6)

**Sprint:** Sprint 4 — Trial Release Readiness and Production Stabilization  
**Dates:** 2026-07-06 – 2026-07-12  
**Sprint Goal:** Enable a production-ready AI Sales Manager experience for the Week 6 trial release by delivering end-to-end lead management capabilities, including campaign execution, AI-driven conversations, analytics, and operational stability.  
**Facilitator:** Scrum Master  
**Participants:** Development Team, Product Owner (customer representative)

---

## What went well

1. **Week 6 trial release shipped on schedule** — SemVer release `v0.4.0` was published from `main` with release notes, Sprint 4 milestone linkage, and pointers to `docs/customer-handover.md` and run instructions. The increment is inspectable by the customer and TA even though several Sprint Backlog items remain open.
2. **Admin Bot and end-to-end workflow matured significantly** — between `v0.3.0` and `v0.4.0` the Admin Bot, inbound listener, and scheduler received the largest share of product changes (~21k lines added across 109 files). The live Sprint Review demo covered business setup, contact upload, first-message preview, campaign launch, typing delays, anti-spam throttling, and lead discovery — a much broader operator path than Sprint 3's MVP v2 focus on prompts and funnel configuration alone.
3. **Lead discovery without paid TGStats API** — `app/services/telegram_global_lead_search.py` and related tests added group-based prospect search and CSV export, aligned with customer feedback to avoid a paid external database. The feature was demonstrated live and produced usable Innopolis-themed results during the review.
4. **Release and runtime hardening reduced demo fragility** — startup no longer fails on common `DEBUG` profile values; placeholder `.env.example` values no longer break API boot; inbound replies respect seller daily and 30-second rate limits; Telegram account API responses no longer leak `session_string`; guardrails emoji detection was fixed. These changes directly support a stable trial handover candidate.
5. **Assignment 6 handover entry points were established** — `docs/customer-handover.md`, `CONTRIBUTING.md`, and `AGENTS.md` describe the actual (not aspirational) transition state, and `README.md` was updated to route customers and reviewers to hosted docs, handover guidance, and contribution workflow.
6. **Automated verification expanded with the product surface** — new modules such as `scripts/qa_audit.py`, `scripts/dialogue_lab.py`, and `scripts/admin_ux_lab.py` plus large test additions for Admin Bot, inbound listener, scheduler, and lead search increased confidence in regressions around the demo path, even where formal Sprint PBIs are still marked open in GitHub.

---

## What did not go well

1. **Sprint 4 milestone tracking diverged from delivered work** — all 11 PBIs assigned to the Sprint 4 milestone (US-06, US-07, US-09, US-015, US-019, TECH-03, TECH-06, TECH-08, TECH-11, TECH-12, TECH-13) remained **open** at Sprint Review, while `v0.4.0` was still released. Inspectors cannot infer Sprint completion from the milestone board alone; Work Status and release scope are misaligned.
2. **Production VPS deployment still incomplete** — TECH-11 and TECH-12 stayed in progress. The July 12 live demo depended on a team member's machine, which contradicted the earlier UAT-1 Pass claim for 24/7 VPS availability. The customer explicitly asked for independent access and stable hosting; that blocker was not resolved inside Sprint 4.
3. **Planned Sprint 4 scope was larger than capacity** — the Sprint Backlog was sized at **40 SP** across five user stories and six technical tasks, while the same Sprint also required Assignment 6 documentation, customer trial meeting, and Week 6 report artefacts. Architecture and process documentation from Sprint 3 had already consumed significant capacity; Sprint 4 repeated the pattern of shipping product increments while formal backlog closure lagged behind.
4. **LLM dialogue quality still blocks customer confidence** — during the live demo the assistant broke character and surfaced system-like behaviour. The customer linked this to model choice and asked to test alternatives through the existing routing API. Prompt hardening and guardrails improved, but the core reliability gap for "marketable" conversations remains.
5. **Lead-search quality and campaign setup friction** — parsing produced mixed relevance (customer: "a matter of quality"), and the operator path still requires multiple approval steps before launch. The customer wants a minimal-setup flow: describe the business, find leads, launch — without verifying every intermediate artefact.
6. **UAT and report traceability gaps** — maintained UAT scenarios still reflect Sprint 3 / MVP v2 execution (2026-07-05). Sprint 4 features shown on July 12 (lead discovery, analytics, manual takeover) lack dedicated UAT IDs and execution results. `reports/week6/README.md` and several Week 6 course artefacts were incomplete at retrospective time.

---

## What changed compared to the previous Sprint

The [Sprint 3 retrospective](../week5/retrospective.md) listed three action points. Sprint 4 response:

| Previous action point | Sprint 4 response |
|---|---|
| Finish VPS deployment before adding new features — treat TECH-11/TECH-12 as Must Have gate. | **Not achieved.** VPS and monitoring PBIs remain open; trial release relied on local Docker and ephemeral localtunnel access. Release hardening and health checks improved, but persistent customer-operable hosting did not land. |
| Time-box documentation and report work at Sprint Planning. | **Partially achieved.** Handover docs (`customer-handover.md`, `CONTRIBUTING.md`, `AGENTS.md`) and Sprint Review summary/transcript were written during the Sprint; canonical `reports/week6/README.md`, UAT updates for Sprint 4 features, and written customer confirmation are still outstanding. |
| Validate architecture diagrams against code on every architecture-touching PR. | **Not explicitly tracked.** Sprint 4 work concentrated on Admin Bot, inbound/scheduler behaviour, and lead search rather than architecture view updates. No new ADRs were required for the lead-search module; existing ADR set (ADR-001–008) remained the maintained baseline. |

Additional changes compared to Sprint 3:

| Area | Sprint 3 (MVP v2, `v0.3.0`) | Sprint 4 (`v0.4.0`) |
|---|---|---|
| Primary focus | Prompt versioning, funnel upload API, production logging/health, automation-rate metric | Operator UX, campaign execution hardening, Telegram group lead search, trial-release stability |
| Admin surface | Script/funnel improvements | Full business → contacts → preview → launch flow; larger FSM and dialogue handling |
| Deployment story | Observability and health checks documented | Release-profile startup fixes; still no customer-owned VPS |
| Test strategy | MVP v2 prompt/funnel/API tests | Massive expansion of bot, scheduler, inbound, and lead-search tests; QA lab scripts |
| Course deliverables | Architecture views, ADRs, Week 5 report skeleton | Assignment 6 Parts 3–4 handover docs; Week 6 Sprint Review artefacts started |
| Customer-facing gap | Natural nurturing flow | Independent trial access, parsing quality, minimal campaign setup, LLM character stability |

---

## Action points

1. **Close the VPS / hosting blocker before Sprint 5 feature work** — finish TECH-11 and TECH-12, reconcile UAT-1 evidence with the actual access path, and update `docs/customer-handover.md` with the real product access artifact URL. Treat persistent hosting as a gate for MVP v3 and written customer confirmation in Week 7.
2. **Reconcile GitHub milestone state with shipped increments** — for each item actually delivered in `v0.4.0`, mark supporting PBIs `Done` or split/re-scope remaining work into explicit Sprint 5 PBIs so the Sprint 4 board reflects inspectable truth. Avoid releasing another SemVer tag while all milestone issues remain open.
