# LLM / AI Usage Report — Week 4 (Assignment 4)

This report describes how the team used AI and LLM tools during the Assignment 4 Sprint. Disclosure is required by the course; all deliverables still reflect original team analysis, review, and acceptance decisions.

---

## Tools used

| Tool | Used by | Primary purpose |
|---|---|---|
| **Cursor (AI-assisted IDE)** | Development team | Code generation, refactoring, test scaffolding, documentation drafts |
| **GitHub Copilot** | Individual developers (occasionally) | Inline code completion in Python and YAML |
| **ChatGPT** | Documentation author | Drafting and structuring markdown reports and acceptance-criteria wording |

No AI tool was used to replace code review, Sprint decisions, or customer-facing commitments. All merged changes were reviewed by a different team member than the implementer.

---

## How they were used

### Code and tests

- **Bug-fix implementation** — AI-assisted suggestions for analytics filtering (`inbound_listener.py`), unique-contact counting (`scheduler.py`), and account eligibility checks. Developers verified behaviour against existing tests and added new cases in `tests/test_core_scheduler.py` and `tests/test_bots_inbound_listener.py`.
- **Quality Requirement Tests** — initial scaffolding for `tests/quality_requirement_tests/` (latency, availability, fault tolerance) was generated with AI help; thresholds and assertions were adjusted manually to match `docs/quality-requirements.md`.
- **CI configuration** — `.github/workflows/ci.yml` bandit job and coverage artifact steps were drafted with AI assistance; the team fixed YAML quoting and pytest version compatibility issues manually after CI runs failed.

### Documentation

- **Quality and testing docs** — `docs/quality-requirements.md`, `docs/quality-requirement-tests.md`, and `docs/testing.md` were outlined with AI help, then edited for accuracy against the actual codebase and ISO/IEC 25010 terminology.
- **Week 4 reports** — structure and first drafts of `reports/week4/README.md`, this retrospective, and reflection sections used AI for formatting; factual content (Sprint scope, delivered changes, customer feedback) was supplied and verified by the team.
- **Roadmap updates** — `docs/roadmap.md` drafts were AI-assisted; Sprint outcomes and next-step PBIs were confirmed against the GitHub milestone and issue board.

### What AI was not used for

- Sprint Planning decisions (which PBIs to select, Story Point estimates, implementer/reviewer assignment).
- Customer Sprint Review or UAT execution.
- Merging PRs without human review.
- Submitting filler or unverified claims in course reports.

---

## Team workflow and quality control

1. **Prompt → edit → test → review** — AI output was never merged as-is. Every change ran through local `pytest`, CI, and a teammate PR review.
2. **Traceability preserved** — issue-linked PRs reference the originating PBI; AI-generated code follows the same workflow as manually written code.
3. **Sensitive data** — no credentials, customer PII, or private recording links were pasted into external AI tools.

---

## Disclosure

The team used AI tools as **productivity aids** during Assignment 4. Meaningful analysis — including quality-requirement rationale, Sprint trade-offs, customer feedback responses, and test design — comes from the team's own work. AI accelerated drafting and boilerplate; humans remained responsible for correctness, review, and submission quality.
