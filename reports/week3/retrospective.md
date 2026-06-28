# Sprint Retrospective

## What went well

1. **MVP v1 scope was delivered on time** — the configurable sales funnel works end-to-end, from database schema to LLM prompts to scheduler integration.
2. **Test coverage remained high** — all 408 tests pass, including new funnel-specific tests, which gave the team confidence to refactor.
3. **Multi-provider LLM abstraction proved valuable** — adding DashScope required only minimal changes, validating the provider-agnostic design.

## What did not go well

1. **Late discovery of schema mismatch** — `sales_funnel` was typed as `Dict` in the schema while the core expected a `List`. Better upfront API/core alignment would have saved rework.
2. **GitHub project setup is manual** — without the GitHub CLI, creating issues, milestones, and project boards took longer than expected.
3. **Customer demo environment was local only** — the lack of a persistent staging deployment made the review harder to share.

## Action points

1. Add API/schema validation checklist to the Definition of Done so type mismatches are caught before implementation.
2. Set up a shared staging environment during Sprint 2 so demos and customer reviews can happen on a live deployment.
