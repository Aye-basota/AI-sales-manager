# Sprint 3 Retrospective (Assignment 5)

**Sprint:** Sprint 3 — MVP v2 (Assignment 5)  
**Dates:** 2026-06-28 – 2026-07-12  
**Sprint Goal:** Deliver MVP v2 by deploying the application to a production VPS for reliable 24/7 availability and enhancing the AI assistant with improved prompts, a more natural conversational flow, and a structured lead nurturing process that builds trust before guiding users through the sales funnel.  
**Facilitator:** Scrum Master  
**Participants:** Development Team, Product Owner (customer representative)

---

## What went well

1. **Architecture documentation and ADRs were completed as maintained assets** — static, dynamic, and deployment views with PlantUML sources, plus four accepted ADRs (ADR-001–ADR-004) linked bidirectionally to quality requirements. The team can now explain *why* guardrails, state machine, scheduler, and anti-repetition checks exist, not only *what* the code does.
2. **Development process and hosted documentation were established** — `docs/development-process.md` with git workflow, MkDocs site on GitHub Pages, and CI link checking give graders and the customer a browsable documentation entry point for MVP v2.
3. **Quality traceability improved across layers** — QR-01–QR-04, QRTs, ADRs, and architecture views reference each other. This supports the course requirement to connect architecture decisions to measurable quality scenarios.
4. **Issue-linked workflow remained consistent** — Part 5 ADRs shipped via reviewed PR #60; documentation changes follow the same branch naming and `Closes #issue` convention as product code.
5. **Sprint Goal alignment on AI conversation quality** — work on prompts, funnel stages, humanizer delays, and guardrails directly targets the customer-facing goal of more natural, trust-building dialogue before CTA.

---

## What did not go well

1. **Production VPS deployment is still in progress** — TECH-11 (Deploy Application to Production VPS) and TECH-12 (Configure Production Infrastructure and Monitoring) remain open. Demos still rely on local Docker or temporary localtunnel access, which conflicts with the Sprint Goal of reliable 24/7 availability.
2. **Large Sprint scope vs. documentation-first delivery** — architecture, process docs, ADRs, and report skeletons consumed significant capacity while US-017 (prompt quality) and US-018 (multi-stage conversation flow) are not yet fully Done.
3. **Week 5 report placeholders accumulated** — UAT execution, demo video, contribution table, and Sprint Review artefacts in `reports/week5/README.md` lag behind documentation and architecture work.
4. **Monolithic container remains an operational risk** — documenting the deployment model clarified that a single `api` container restart affects scheduler, inbound listeners, and Admin Bot simultaneously; no split-worker mitigation was implemented in this Sprint.

---

## What changed compared to the previous Sprint

The [Sprint 2 retrospective](../week4/retrospective.md) listed two action points. Sprint 3 response:

| Previous action point | Sprint 3 response |
|---|---|
| Limit Sprint Backlog to a realistic subset; mark quality gates as non-negotiable. | Partially addressed. Architecture and documentation PBIs were completed to Definition of Done, but VPS deployment and full AI conversation PBIs remain in progress. Quality gates (CI, QRTs) stayed active on `main`. |
| Complete report artefacts in parallel with code, not after. | Partially addressed. Architecture views, ADRs, development-process doc, and this retrospective were written during the Sprint; UAT summary, demo video, and contribution table are still placeholders. |

Additional changes compared to Sprint 2:

- **Shift from quality-only increment to architecture + MVP v2 product scope** — Sprint 2 focused on QRTs and bug fixes (v0.2.0); Sprint 3 adds maintained architecture assets and AI conversation improvements toward v0.3.0.
- **Introduction of ADRs and architectural views** — new maintained assets under `docs/architecture/` that must stay current in future sprints.
- **Hosted documentation site** — MkDocs on GitHub Pages replaces README-only documentation discovery.
- **Sprint Goal reframed around deployment and AI UX** — explicit customer value on VPS availability and natural lead nurturing, not only internal quality automation.

---

## Concrete improvements for the next Sprint

1. **Finish VPS deployment before adding new features** — treat TECH-11 and TECH-12 as Must Have gate for Sprint Review; do not defer production hosting again. Define a minimal monitoring checklist (health endpoint, container restart policy, backup cadence) as part of Done.
2. **Time-box documentation and report work at Sprint Planning** — assign owners and mid-Sprint deadlines for UAT summary, demo video, and `reports/week5/README.md` placeholders so submission artefacts do not block the final week.
3. **Validate architecture diagrams against code on every architecture-touching PR** — add a reviewer checklist item: static/dynamic/deployment `.puml` sources still match module names and integration boundaries in `app/`.
