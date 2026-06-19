# Definition of Done

This document defines the minimum completion standard for every Product Backlog Item (PBI) in this project.

## General Criteria

A PBI is considered **Done** only when all of the following are true:

1. **Code implemented** — the functionality described by the PBI is implemented on a feature branch.
2. **Tests pass** — all existing tests continue to pass, and new tests are added for the implemented behavior.
3. **Code reviewed** — at least one team member has reviewed and approved the linked pull request.
4. **Acceptance criteria verified** — every acceptance criterion is explicitly checked and evidenced in the PR description or comments.
5. **No regressions** — the change does not break the build, API contracts, or existing user flows.
6. **Documentation updated** — user-facing changes are reflected in `README.md`, API docs, or other relevant documentation.
7. **CHANGELOG updated** — user-visible changes are recorded in `CHANGELOG.md` under `[Unreleased]` or the appropriate release.
8. **Merged to main** — the linked PR is merged using a merge commit on the protected default branch.
9. **Issue closed** — the related issue is closed with the `Done` work status.

## MVP v1 Specific Criteria

For PBIs marked as part of **MVP v1**, the following also apply:

- At least three acceptance criteria are defined before implementation starts.
- The PBI is assigned to the current Sprint milestone.
- Manual verification or integration test evidence is attached to the PR.
- The implemented increment is demonstrable in the running application.

## Quality Standards

- Code follows the existing project style (PEP 8, type hints where applicable).
- No secrets, API keys, or credentials are committed.
- LLM-generated code is reviewed, tested, and understood by the team.
- UI/UX changes are manually checked on desktop and mobile where relevant.
