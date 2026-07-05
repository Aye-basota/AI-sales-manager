# Sprint Review Summary — Week 5 (Sprint 3, MVP v2)

**Date:** 2026-07-05
**Participants:** Development team, Mark (customer / stakeholder)
**Format:** Combined recorded session (customer-executed UAT + Sprint Review discussion). Moodle-only timecodes mark where each segment occurs; see the private Moodle submission.

## Sprint Goal Reviewed

Deliver MVP v2 by (1) deploying the application to a production VPS for reliable 24/7 availability, and (2) improving the AI assistant's conversational quality through enhanced prompts, a more natural dialogue flow, and an optimized lead-nurturing process.

## Delivered Increment Discussed

* **Production deployment:** The application is now hosted on a production VPS, independent of any developer's local machine, with associated infrastructure/monitoring configuration (TECH-11, TECH-12).
* **Conversational quality:** Reworked system prompts (TECH-13, US-017) and a new multi-stage conversation flow (US-018) that guide users toward booking/purchase through clarifying questions and consultative responses, instead of returning flat answers.

## UAT Results

Both new UAT scenarios for MVP v2, plus the existing regression scenario, were executed live with the customer:

|Scenario|Result|
|-|-|
|Regression: standard Q\&A + off-topic handling|✅ Pass|
|New: 24/7 availability via VPS (verified with local dev environment fully shut down)|✅ Pass|
|New: natural conversational flow / lead nurturing|✅ Pass|

No scenarios failed. See `docs/user-acceptance-tests.md` for full acceptance criteria and execution details.

## Addressed Customer Feedback

Feedback from a prior session regarding response reliability and bot availability outside working hours has been addressed through the VPS deployment; the customer confirmed this directly during the session.

## Architecture / Workflow Changes Discussed

* Migration from local, developer-machine-hosted execution to a dedicated production VPS.
* Infrastructure and monitoring configuration to support production operation (see TECH-12; ADR updates in `docs/architecture/adr/`).
* Prompt/dialogue architecture updated to support multi-stage, nurturing-oriented conversation flow rather than single-turn Q\&A.

## Remaining Gaps, Risks, and Follow-up

* **New feedback / gap identified:** The admin panel does not currently allow returning to a previous step (e.g., after confirming a campaign launch) to edit or correct data. This creates friction for the customer when managing campaigns and contact uploads.
* **Follow-up action:** A new backlog item will be created to address admin panel navigation/edit flow, targeted for Sprint 4.

## Product Backlog Updates

\- \[US-019: Improve Admin Panel Navigation — Allow Editing After Campaign Launch Step](https://github.com/Aye-basota/AI-sales-manager/issues/68) (#68), created directly from customer feedback in this session.

