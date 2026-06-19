# Definition of Done (DoD)

This document defines the team's shared minimum completion standard for the AI Sales Manager project. A Product Backlog Item (PBI) or User Story is only considered "Done" when all the following criteria are met.

## 1. Code & Implementation
- [ ] The code implements the clear expected outcome and description specified in the PBI.
- [ ] For User Stories: All linked supporting PBIs required to satisfy its acceptance criteria are fully completed.
- [ ] The work is successfully integrated without breaking existing functionality (e.g., Telegram/WhatsApp agent integrations).

## 2. Testing & Verification
- [ ] All specific, observable, and testable Acceptance Criteria attached to the PBI are fully satisfied.
- [ ] Verification evidence proving that the Acceptance Criteria are met is recorded and linked (e.g., attached to the PR/MR or issue).
- [ ] The application and its updates have been successfully tested locally.

## 3. Workflow & Review
- [ ] A Pull Request (PR) / Merge Request (MR) is created and explicitly linked to the issue to maintain full traceability.
- [ ] The code is reviewed and approved by a **different** team member than the implementer.
- [ ] All review comments, questions, and discussions on the PR/MR are resolved.

## 4. Documentation
- [ ] **`CHANGELOG.md` is updated** with a clear entry for any user-visible changes.
- [ ] Traceability is maintained (e.g., stable User Story IDs are preserved; `docs/user-stories.md` is updated if the requirement status or Sprint assignment changed).
- [ ] System documentation (README.md, launch guides, or interface specifications) is updated if the PBI introduces architectural, workflow, or configuration changes.
