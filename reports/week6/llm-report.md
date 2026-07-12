# LLM / AI Usage Report — Week 6 (Assignment 6, Sprint 4)

> **Note on this revision:** this file was originally committed as a byte-for-byte copy of `reports/week5/llm-report.md` (still titled "Week 5 (Assignment 5)" and describing Assignment 5 tool usage). The section below verifies and re-labels one team member's Week 6 usage. The team-wide tool table carried over from Week 5 is kept for reference but is **unconfirmed for Sprint 4** — mark each row confirmed/updated or removed before submission; do not assume it is accurate for this sprint just because it was accurate for the last one.

Disclosure is required by the course; all deliverables still reflect original team analysis, review, and acceptance decisions.

---

## Verified: Claude Code (Anthropic, Sonnet 5) — issammerdas05, Week 6

Used during Week 6 doc-currency and reporting work, specifically to:

- Review `README.md`, `CONTRIBUTING.md`, `AGENTS.md`, and `docs/customer-handover.md` against the Assignment 6 Part 3/4 checklist and identify gaps (staleness relative to the Sprint 4 VPS deployment and Sprint Review outcome).
- Draft the corresponding edits to `README.md` and `docs/customer-handover.md`, reviewed by the team member before being pushed as a PR rather than applied unreviewed.
- Investigate a file-placement bug where Week 6 Sprint Review content had been committed under `reports/week5/`, cross-check it against git history and `reports/week5/README.md`'s existing links, and (in coordination with a teammate who was independently fixing the same issue) move/rename the affected files into `reports/week6/`.
- Query the GitHub REST API (public, unauthenticated reads only) for milestone, issue, and PR data used to populate `reports/week6/README.md` with verifiable links and numbers rather than estimates.
- Draft `reports/week6/README.md` itself from that verified data, and identify this file's Week 5/Week 6 mislabeling.

All generated text was reviewed before being committed; PBI status claims, the SemVer release, and the transition-status wording were cross-checked against actual repository/GitHub state (commits, tags, issues, milestones) rather than taken from the model's own assertions.

---

## Unconfirmed for Sprint 4 — inherited from the Week 5 report

> **TODO (team):** confirm whether the tools below were actually used again during Sprint 4 (2026-07-06 – 2026-07-12), and by whom, or remove this section if it was Assignment-5-only usage that got copied here by mistake.

| Tool | Used by | Primary purpose (as claimed for Assignment 5) |
|---|---|---|
| **Cursor (AI-assisted IDE)** | Development team | Architecture documentation, ADR drafting, PlantUML diagram scaffolding, report writing, code navigation |
| **GitHub Copilot** | Individual developers (occasionally) | Inline completion in Python, YAML, and Markdown |
| **ChatGPT** | Documentation author | Structuring acceptance criteria, retrospective wording, and report outlines |

No AI tool was used to replace code review, Sprint Planning decisions, customer UAT execution, or Sprint Review facilitation. All merged changes were reviewed by a different team member than the implementer where applicable.

---

## What AI was not used for

- Sprint Planning (PBI selection, Story Points, implementer/reviewer assignment).
- Customer Sprint Review, UAT execution, or the 2026-07-12 customer trial session itself.
- Merging PRs without human review.
- Pasting credentials, customer PII, or private recording links into external AI tools.
- Submitting unverified architecture, release, or transition-status claims not grounded in the repository or GitHub.

---

## Disclosure

The team used AI tools as **productivity aids**. Sprint trade-offs, customer feedback interpretation, and transition-status decisions come from the team's own work and the actual Sprint Review session. AI accelerated drafting of documentation and report structure; humans remained responsible for accuracy, review, and submission quality.

The product itself uses external LLM APIs (OpenRouter / DashScope) for **runtime message generation** — that is product functionality, not course tooling. This report covers **development-time** AI tool usage only.
