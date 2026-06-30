# Definition of Done (DoD)

This document defines the team's shared minimum completion standard for the AI Sales Manager project. A Product Backlog Item (PBI) or User Story is only considered "Done" when all the following criteria are met.

## 1. Code & Implementation
- [ ] The code implements the clear expected outcome and description specified in the PBI.
- [ ] For User Stories: All linked supporting PBIs required to satisfy its acceptance criteria are fully completed.
- [ ] The work is successfully integrated without breaking existing functionality (e.g., Telegram/WhatsApp agent integrations, campaign scheduling, inbound message handling).
- [ ] New or changed code follows the existing project style and passes linting (`ruff check`) and formatting checks (`ruff format --check`).

## 2. Testing & Verification
- [ ] All specific, observable, and testable Acceptance Criteria attached to the PBI are fully satisfied.
- [ ] Verification evidence proving that the Acceptance Criteria are met is recorded and linked (e.g., attached to the PR/MR or issue).
- [ ] Automated tests are added or updated for the changed product area. Tests must credibly cover the new behavior and would fail without the change.
- [ ] All tests pass locally and in CI: unit tests, integration tests, and automated Quality Requirement Tests (QRTs).
- [ ] Line coverage for critical modules remains at or above the project threshold (currently ≥ 30%).
- [ ] Relevant quality requirements and QRTs are satisfied, or explicitly documented as not applicable.

## 3. Architecture & Quality
- [ ] If the PBI changes architecture, critical modules, deployment model, workflow, or CI configuration, the architecture documentation and/or related Architecture Decision Records (ADRs) are updated.
- [ ] Each affected quality requirement links to at least one related ADR where applicable (see [`docs/quality-requirements.md`](quality-requirements.md)).

## 4. Workflow & Review
- [ ] A Pull Request (PR) / Merge Request (MR) is created and explicitly linked to the issue to maintain full traceability.
- [ ] The code is reviewed and approved by a **different** team member than the implementer.
- [ ] All review comments, questions, and discussions on the PR/MR are resolved.
- [ ] CI quality gates pass before merge:
  - Linting and formatting (`ruff`)
  - Unit, integration, and QRT tests with coverage (`pytest`)
  - Security static analysis (`bandit`)
  - Dependency vulnerability scan (`pip-audit`)
  - Broken-link check (`lychee`)

## 5. Documentation
- [ ] **`CHANGELOG.md` is updated** with a clear entry for any user-visible changes.
- [ ] Traceability is maintained (e.g., stable User Story IDs are preserved; `docs/user-stories.md` is updated if the requirement status or Sprint assignment changed).
- [ ] System documentation ([`README.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/README.md), [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md), or [`docs/interface.md`](interface.md)) is updated if the PBI introduces architectural, workflow, configuration, or usage changes.
- [ ] [`docs/testing.md`](testing.md), [`docs/quality-requirements.md`](quality-requirements.md), and [`docs/quality-requirement-tests.md`](quality-requirement-tests.md) are updated if the PBI affects quality requirements, test coverage, or CI gates.
- [ ] The Week 5 public report ([`reports/week5/README.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/reports/week5/README.md)) is updated with relevant links, screenshots, and status when the PBI is part of the delivered `MVP v2` increment.

## 6. Release & Deployment
- [ ] For PBIs included in `MVP v2`: the code is merged into the protected default branch (`main`).
- [ ] A SemVer release (`v0.3.0`) is created for the `MVP v2` increment and links to the Sprint 3 milestone, deployment instructions, public demo video, and Week 5 report.
- [ ] The current product increment remains deployed and accessible to the customer and TA until grading is complete.
