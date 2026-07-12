# Contributing

Thanks for contributing to AI Sales Manager. This document describes how the team actually works in this repository — for the full rationale behind the workflow, see [`docs/development-process.md`](docs/development-process.md).

## Before You Start

1. Read the root [`README.md`](README.md) for what the product does and how to run it.
2. Set up a local environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env       # fill in your own keys, see docs/customer-handover.md
   alembic upgrade head
   pytest tests/ -v
   ```

   Or with Docker: `docker-compose up -d --build` then `docker-compose exec api alembic upgrade head`.
3. Never commit `.env`, `*.session` files, or any real credential. `.gitignore` already excludes them — do not remove those entries.

## Workflow

1. **Create a GitHub Issue** for the change (user story, bug, or task). Every change should trace back to an issue.
2. **Create a branch from `main`** named `<issue-number>-short-description`, e.g. `53-week6-trial-release-hardening`.
3. **Commit** in small, focused commits on that branch.
4. **Open a Pull Request** that references the issue (`closes #N`) and describes what changed and how it was tested.
5. **Get at least one review** from a different team member. PR authors do not approve their own PRs.
6. **Wait for CI to pass** (see below) before merging.
7. **Merge with a merge commit** — do not squash or rebase. This preserves full history for traceability.
8. Delete the feature branch after merge.

`main` is the protected default branch. Direct pushes to `main` are not allowed — all changes go through a reviewed PR, including documentation-only changes.

## Required Checks Before Merge

These run in CI (`.github/workflows/ci.yml`) on every PR and on every push to `main`:

| Check | Command | Notes |
|---|---|---|
| Tests + coverage | `pytest tests/ -v --cov=app --cov-report=term-missing` | Fails if coverage drops below 30% |
| Security static analysis | `bandit -r app/ -ll` | |
| Dependency vulnerability scan | `pip-audit --requirement requirements.txt --desc` | |
| Lint | `flake8 app/ --max-line-length=120 --extend-ignore=E203,W503` | |

The repository also runs a link checker (`.github/workflows/links.yml`) across Markdown files, including everything under `reports/`.

Run the same commands locally before opening a PR to avoid CI surprises.

## Definition of Done

A change is not ready to merge until it satisfies the team's [Definition of Done](docs/definition-of-done.md), which requires (at minimum): acceptance criteria met, review approval, passing tests/CI, `CHANGELOG.md` updated for user-visible changes, and any affected maintained docs (`docs/`) updated in the same PR.

## Changelog

If your change is user-visible, add an entry under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md) using the `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security` categories from [Keep a Changelog](https://keepachangelog.com/). If it is not user-visible (internal refactor, test-only change, docs typo), say so in the PR description instead.

## Documentation Changes

If your change affects setup, deployment, architecture, quality requirements, or the current handover state, update the relevant file in the same PR:

- Product usage/setup: [`README.md`](README.md), [`LAUNCH_GUIDE.md`](LAUNCH_GUIDE.md)
- Handover/transition state: [`docs/customer-handover.md`](docs/customer-handover.md)
- Architecture: [`docs/architecture/README.md`](docs/architecture/README.md) and any relevant ADR in `docs/architecture/adr/`
- Quality/testing: [`docs/quality-requirements.md`](docs/quality-requirements.md), [`docs/testing.md`](docs/testing.md)

Stale documentation is treated as a defect, not a formality.

## Working With an AI Coding Agent

If you're using an AI coding assistant (Claude Code, Copilot, Cursor, etc.) to contribute, also read [`AGENTS.md`](AGENTS.md) — it defines the safety constraints and conventions the agent should follow in this repository.
