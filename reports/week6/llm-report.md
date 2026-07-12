# Week 6 LLM Usage Report

> **Team-only: partially a placeholder.** The section below discloses one team member's use of Claude Code for a specific, identifiable slice of Week 6 work. The rest of the team must add their own tool usage (what was used, for what, and how output was reviewed/edited) before the Week 6 submission. Do not submit this file without that.

## Claude Code (Anthropic, Sonnet 5) — issammerdas05

Used during Week 6 doc-currency and reporting work, specifically to:

- Review `README.md`, `CONTRIBUTING.md`, `AGENTS.md`, and `docs/customer-handover.md` against the Assignment 6 Part 3/4 checklist and identify gaps (staleness relative to the Sprint 4 VPS deployment and Sprint Review outcome).
- Draft the corresponding edits to `README.md` and `docs/customer-handover.md`, which were reviewed and pushed by the team member as PRs rather than applied unreviewed.
- Investigate a file-placement bug where Week 6 Sprint Review content had been committed under `reports/week5/`, cross-check it against git history and `reports/week5/README.md`'s existing links, and (in coordination with the teammate who independently fixed the same issue) move/rename the affected files into `reports/week6/`.
- Query the GitHub REST API (public, unauthenticated reads only) for milestone, issue, and PR data used to populate `reports/week6/README.md` with verifiable links and numbers rather than estimates.
- Draft `reports/week6/README.md` itself from that verified data.

All generated text was reviewed before being committed; PBI status claims, the SemVer release, and the transition-status wording were cross-checked against actual repository/GitHub state (commits, tags, issues, milestones) rather than taken from the model's own assertions.

## Other tools used by the team during Sprint 4

- TODO — each team member should add what they used (LLM tools, Copilot, etc.), for which tasks, and how they verified/edited the output.
