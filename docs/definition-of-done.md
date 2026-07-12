# Definition of Done — AI Sales Manager

A Product Backlog Item (PBI) may only be marked **Done** when every item in this checklist is satisfied.
This Definition of Done applies to all Sprint work from Assignment 4 onward.

---

## Checklist

### 1. Acceptance Criteria Verification
- [ ] All acceptance criteria defined on the issue are met and verified by the implementer
- [ ] Edge cases described in the acceptance criteria have been manually tested or covered by automated tests

### 2. Review by Another Team Member
- [ ] The PR/MR has been reviewed and approved by at least one team member who is **not** the implementer
- [ ] A named backup reviewer is available if the primary reviewer is blocked for more than 24 hours
- [ ] All reviewer comments are resolved before merge

### 3. Passing CI Checks
- [ ] The `test` CI job passes — all pytest tests green with no regressions
- [ ] The `security` CI job passes — Bandit reports no new medium or high severity issues (`bandit -r app/ -ll`)
- [ ] The `pip-audit` CI job passes — no known vulnerabilities in dependencies
- [ ] The `lint` CI job passes — flake8 reports no errors (`flake8 app/ --max-line-length=120`)
- [ ] The `link-check` CI job passes — no broken links in Markdown files (`lychee`)
- [ ] CI runs on the protected default branch (`main`) and shows a green status before merge

### 4. Relevant Automated Tests
- [ ] New logic is covered by at least one automated unit or integration test
- [ ] All existing tests continue to pass after the change
- [ ] Tests are stored in `tests/` following the existing naming convention (`test_<module>.py`)
- [ ] Tests are linked from `docs/testing.md` if they cover a new module or component

### 5. Relevant Automated Quality Requirement Tests
- [ ] If the change affects `app/core/state_machine.py` → `tests/test_core_state_machine.py` still passes (QRT-02)
- [ ] If the change affects `app/llm/guardrails.py` → `tests/test_llm_guardrails.py` still passes (QRT-01, QRT-04)
- [ ] If the change affects `app/core/scheduler.py` → `tests/test_core_scheduler.py` still passes (QRT-03)
- [ ] If the change introduces a new quality requirement → a linked QRT is defined in `docs/quality-requirement-tests.md`
- [ ] If the change introduces or affects an architecture decision → the related ADR in `docs/architecture/adr/` is updated or created

### 6. Coverage Expectations for Critical Modules
- [ ] Each critical module maintains at least **30% line coverage** after the change:

  | Module | Minimum coverage |
  |---|---|
  | `app/core/state_machine.py` | 30% (currently ~100%) |
  | `app/llm/engine.py` | 30% (currently ~99%) |
  | `app/llm/guardrails.py` | 30% (currently ~98%) |
  | `app/services/notification_service.py` | 30% (currently ~96%) |
  | `app/core/scheduler.py` | 30% (currently ~80%) |
  | `app/bots/inbound_listener.py` | 30% (currently ~75%) |
  | `app/services/conversation_service.py` | 30% (currently ~70%) |
  | `app/core/humanizer.py` | 30% (currently ~68%) |

- [ ] Coverage report is visible in CI artifacts or PR/MR comments

### 7. Testing Evidence Preserved
- [ ] CI run link is attached to the PR/MR or issue before closing
- [ ] Coverage report or screenshot is included in the PR/MR description or linked from the CI run
- [ ] If a QRT was added or modified, the evidence is linked from `docs/quality-requirement-tests.md`

### 8. Changelog Update for User-Visible Changes
- [ ] If the change is user-visible (new feature, bug fix, behavior change), an entry is added to `CHANGELOG.md` under `[Unreleased]`
- [ ] Format follows Keep a Changelog: `### Added`, `### Fixed`, `### Changed`, `### Removed`
- [ ] Internal refactors, test additions, and documentation-only changes do not require a changelog entry

### 9. Release and Deployment Evidence (for Assignment 6 increments)
- [ ] The change is merged into the protected default branch (`main`) through an issue-linked PR/MR
- [ ] A SemVer release is created for each required submitted increment and links to:
  - Relevant Sprint milestone
  - Deployment or run instructions
  - Relevant public report (`reports/week6/README.md` for the Week 6 trial release; `reports/week7/README.md` for final `MVP v3`)
  - Customer handover guidance where required
  - Public sanitized demo video where the assignment requires it
- [ ] The current product increment remains deployed and accessible to the customer and TA until grading is complete
- [ ] The relevant weekly public report is updated with links, screenshots, access status, release status, and known limitations

---

## Maintenance

If later project work changes any of the following, this file must be updated **in the same PR/MR**:

- Product stack (new language, framework, or runtime)
- Quality requirements (`docs/quality-requirements.md`)
- Critical modules list or coverage thresholds
- CI configuration (`.github/workflows/ci.yml`)
- QRT files (`docs/quality-requirement-tests.md`)

Do not leave Assignment 4 gates stale when the product evolves.
