# LLM / AI Usage Report — Week 5 (Assignment 5)

This report describes how the team used AI and LLM tools during the Assignment 5 Sprint (MVP v2). Disclosure is required by the course; all deliverables still reflect original team analysis, review, and acceptance decisions.

---

## Tools used

| Tool | Used by | Primary purpose |
|---|---|---|
| **Cursor (AI-assisted IDE)** | Development team | Architecture documentation, ADR drafting, PlantUML diagram scaffolding, report writing, code navigation |
| **GitHub Copilot** | Individual developers (occasionally) | Inline completion in Python, YAML, and Markdown |
| **ChatGPT** | Documentation author | Structuring acceptance criteria, retrospective wording, and report outlines |

No AI tool was used to replace code review, Sprint Planning decisions, customer UAT execution, or Sprint Review facilitation. All merged changes were reviewed by a different team member than the implementer where applicable.

---

## How they were used

### Architecture documentation (Part 4)

- **PlantUML diagram drafts** — component, sequence, and deployment diagram `.puml` sources were scaffolded with AI assistance from the actual module layout (`app/bots/`, `app/core/`, `app/llm/`, `docker-compose.yml`). The team verified component names, integration paths, and ADR references against the codebase before commit.
- **`docs/architecture/README.md` and view READMEs** — AI helped structure sections required by Assignment 5 (coupling/cohesion analysis, scenario rationale, deployment trade-offs). Factual claims about scheduler interval, guardrail checks, and Docker services were checked against source files.

### ADRs and quality traceability (Part 5 — prior PR)

- **ADR expansion** — context, alternatives, and consequences sections for ADR-001–ADR-004 were drafted with AI help, then aligned with `docs/quality-requirements.md` and existing tests in `tests/test_llm_guardrails.py`, `tests/test_core_state_machine.py`, and `tests/test_core_scheduler.py`.

### Sprint reports (Parts 10, 12, 14)

- **Retrospective and reflection** — structure and first drafts of `reports/week5/retrospective.md` used AI for formatting; Sprint outcomes, open PBIs (TECH-11, US-017, US-018), and comparison to Sprint 2 action points were supplied and verified by the team.
- **This LLM report** — AI assisted with section layout; tool usage claims reflect actual team practice.

### Product and prompt work (Sprint Goal)

- **Prompt and conversation flow improvements** — developers used Cursor to explore prompt templates in `app/llm/prompts.py` and inbound handler logic; final prompt text and funnel stage behaviour were reviewed manually and tested against existing guardrail and state machine tests.
- **No autonomous AI commits** — AI suggestions for product code followed the same prompt → edit → test → review workflow as Assignment 4.

### What AI was not used for

- Sprint Planning (PBI selection, Story Points, implementer/reviewer assignment).
- Customer Sprint Review or recorded UAT sessions.
- Merging PRs without human review.
- Pasting credentials, customer PII, or private recording links into external AI tools.
- Submitting unverified architecture claims not grounded in the repository.

---

## Team workflow and quality control

1. **Prompt → edit → verify → review** — AI-generated documentation was checked against source code, ADRs, and Process Requirements before merge.
2. **Traceability preserved** — issue-linked PRs reference Assignment 5 parts and originating issues; AI-assisted docs follow the same workflow as manually written docs.
3. **Diagrams-as-code** — PlantUML sources live in the repository (`docs/architecture/*/`) so architecture changes remain reviewable in PRs rather than as opaque image exports only.

---

## Disclosure

The team used AI tools as **productivity aids** during Assignment 5. Architecture reasoning, Sprint trade-offs, retrospective analysis, and quality-requirement traceability come from the team's own work. AI accelerated drafting of diagrams, ADRs, and report structure; humans remained responsible for accuracy, review, and submission quality.

The product itself uses external LLM APIs (OpenRouter / DashScope) for **runtime message generation** — that is product functionality, not course tooling. This report covers **development-time** AI tool usage only.
