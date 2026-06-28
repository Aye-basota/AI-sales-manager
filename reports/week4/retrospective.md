# Sprint 2 Retrospective (Assignment 4)

**Sprint:** Sprint 2 — Assignment 4  
**Dates:** 2026-06-25 – 2026-06-28 (increment delivered as v0.2.0)  
**Facilitator:** Scrum Master  
**Participants:** Development Team, Product Owner (customer representative)

---

## What went well

1. **Quality automation was established end-to-end** — three ISO/IEC 25010 quality requirements (time behaviour, availability, fault tolerance) were defined and backed by automated QRTs in CI. This gives the team measurable gates instead of ad-hoc manual checks.
2. **Critical bugs were fixed before release** — analytics no longer count replies for paused/closed campaigns, `processed_contacts` counts unique contacts, and assigned-account selection validates eligibility with fallback. These fixes directly address demo and operational risks.
3. **Test suite remained stable and grew** — 430+ tests pass, including new QRTs, scheduler tests, and API fault-tolerance coverage. High coverage on critical modules (scheduler, state machine, LLM engine) increased confidence during refactoring.
4. **Release v0.2.0 shipped with traceability** — CHANGELOG, SemVer tag, demo seed script, and localtunnel deployment path make the increment accessible for customer review and TA grading.
5. **Team collaboration on reviews** — issue-linked PRs (#39, #40, and follow-up fixes) were reviewed by different team members, maintaining the workflow evidence required by the course.

---

## What did not go well

1. **Sprint scope was broader than capacity** — many campaign-launch PBIs (US-011, US-012, TECH-07–TECH-10) remain open. The team pivoted to quality and reliability work, which was the right trade-off for Assignment 4, but campaign launch is still incomplete.
2. **Deployment is still not a persistent staging environment** — localtunnel provides temporary public access, but there is no always-on hosted instance. This makes customer demos dependent on a team member running Docker locally.
3. **Week 4 report artefacts lagged behind code** — several report sections (UAT results, demo video, contribution table) were left as placeholders while product and CI work progressed first.
4. **CI required follow-up fixes after release** — lint job, pytest version compatibility, and YAML quoting issues were discovered post-merge and needed additional commits on `main`.

---

## What changed compared to the previous Sprint

The [Sprint 1 retrospective](../week3/retrospective.md) listed two action points. Here is how Sprint 2 responded:

| Previous action point | Sprint 2 response |
|---|---|
| Add API/schema validation checklist to the Definition of Done so type mismatches are caught before implementation. | Partially addressed. Invalid JSON now returns HTTP 400 (QRT-003), and `docs/definition-of-done.md` was extended with CI and testing gates. A dedicated schema-validation checklist item is still missing from the DoD. |
| Set up a shared staging environment so demos and customer reviews can happen on a live deployment. | Partially addressed. Added `docker-compose.tunnel.yml` and `scripts/start_localtunnel.sh` for temporary public access via localtunnel. A persistent staging host was not provisioned. |

Additional process changes compared to Sprint 1:

- Sprint planning moved from MVP feature delivery to **quality-first increment** work (QRTs, bandit, coverage artifacts).
- Customer feedback from Week 3 (empty demo view) was addressed with `scripts/seed_demo_data.py`.
- Release discipline improved: SemVer v0.2.0 with CHANGELOG entries and linked milestone evidence.

---

## Process improvements for the next Sprint

1. **Limit Sprint Backlog to a realistic subset and mark quality gates as non-negotiable** — before Sprint Planning, cap selected PBIs to what the team can bring to full Definition of Done (including CI, tests, and changelog). Defer remaining campaign-launch items explicitly rather than carrying them as implicit scope.
2. **Complete report artefacts in parallel with code, not after** — assign ownership of Week 5 report sections (UAT summary, demo video, contribution table) at Sprint Planning so placeholders do not accumulate at submission time.
