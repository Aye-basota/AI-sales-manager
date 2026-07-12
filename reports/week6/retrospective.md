# Week 6 Retrospective

## What went well

- The team demonstrated an end-to-end product workflow to the customer, including setup, contact upload, campaign launch, conversation behavior, and lead discovery.
- The automated test suite is strong and broad; the local audit passed with 974 tests.
- Customer feedback was concrete enough to become Sprint 5 follow-up work.
- Public handover and contributor/agent guidance now exist in the repository.

## What did not go well

- Week 6 evidence was initially scattered across Week 5 files and did not match the Assignment 6 required folder structure.
- The latest public CI run was blocked by flake8 line-length errors until the regex formatting fix.
- The Week 6 trial access/deployment story initially mixed bot access, web/API hosting, and final customer-side transition.
- The public report initially missed embedded screenshots and the actual Week 6 release link.

## What the team changed or attempted to change based on the previous Sprint Retrospective, and what results they observed

- The team moved from documentation-only planning toward a live customer trial, which produced more actionable feedback.
- CI and QA checks remained active and exposed a real lint issue quickly.
- Handover documentation was added, and the team clarified that Week 6 evidence is a team-controlled bot trial rather than final customer-side operation.

## Action points

1. Before finalizing any future weekly report, verify that every required artifact is in the correct `reports/weekN/` folder.
2. Treat access/deployment truth as a release blocker: no release/report should claim a trial or handover level without a link or private evidence path.
