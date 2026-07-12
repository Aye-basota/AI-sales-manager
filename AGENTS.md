# AGENTS

Operating instructions for AI coding agents (Claude Code, Copilot, Cursor, or similar) working in this repository. Human contributors should read [`CONTRIBUTING.md`](CONTRIBUTING.md) instead; this file is agent-specific.

## Repository Map

- `app/` — FastAPI backend: `api/` (routes), `bots/` (Telegram Admin Bot + seller MTProto client + inbound listener), `core/` (funnel, state machine, scheduler, humanizer), `llm/` (prompt engine, guardrails, intent classification), `models/` / `schemas/` (SQLAlchemy + Pydantic), `services/` (contact import, lead discovery, notifications).
- `tests/` — pytest suite, including `tests/quality_requirement_tests/` for automated QRTs.
- `docs/` — maintained product documentation (architecture, quality requirements, testing, roadmap, customer handover). Treat these as living documents, not one-time write-ups.
- `reports/weekN/` — course-assignment evidence (Sprint reports, retrospectives, reflections). Not product documentation — don't conflate the two.
- `alembic/` — database migrations.
- `scripts/` — operational scripts (session generation, demo data seeding, lead import).

## Commits

- Follow conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, etc.).
- Reference the linked GitHub issue in the commit body or PR description where applicable.
- Inspect `git status` and `git diff` before committing; stage only the files that belong to the change.
- Do not amend or rewrite history on `main` or on branches other than the one you are actively working on.

## Workflow Constraints

- `main` is protected: never push directly to it. Work on an issue-linked branch named `<issue-number>-short-description` and open a PR, per [`docs/development-process.md`](docs/development-process.md).
- Do not squash or rebase-merge — this repo uses merge commits to preserve traceability.
- Do not disable, skip, or narrow an existing test, CI check, or quality gate to make a change pass. If a check is genuinely obsolete, replace it with an equivalent or stronger one and say so explicitly in the PR description.
- Do not bypass pre-commit hooks or CI with flags like `--no-verify`.

## Before Considering a Change Done

Run the same checks CI runs (see `.github/workflows/ci.yml`):

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
bandit -r app/ -ll
pip-audit --requirement requirements.txt --desc
flake8 app/ --max-line-length=120 --extend-ignore=E203,W503
```

Update `CHANGELOG.md` under `[Unreleased]` for any user-visible change, and update the relevant file under `docs/` if the change affects architecture, quality requirements, testing strategy, or the customer handover state (`docs/customer-handover.md`).

## Safety Constraints

- Never commit `.env`, `*.session` files, API keys, Telegram session strings, or any other secret. `.gitignore` already excludes these — do not remove those entries or work around them.
- Never hardcode or print a real Telegram session string, LLM API key, or database credential in code, logs, tests, or commit messages. Use `.env.example` placeholders and environment variables only.
- Do not commit real customer names, phone numbers, emails, or other PII into the repository, screenshots, or public documentation. Use sanitized examples or GitHub usernames/roles instead, per the sanitization expectations described in the course requirement files.
- Do not fabricate customer feedback, UAT results, test data, or contribution history. If information needed for a report or doc (e.g. `docs/customer-handover.md`, contribution tables) isn't verifiable from the repository or GitHub, say so explicitly rather than inventing it.
- `docs/customer-handover.md` must describe the actual current handover state. Do not write it as an aspirational future state — update it only to match what has actually happened.
- Do not deploy, expose, or share access to any live instance without checking with a team member — the product sends real Telegram messages from a live account.

## Where to Look First

- Product usage / setup: [`README.md`](README.md), [`LAUNCH_GUIDE.md`](LAUNCH_GUIDE.md)
- Contribution workflow: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Development process and git workflow: [`docs/development-process.md`](docs/development-process.md)
- Architecture and ADRs: [`docs/architecture/README.md`](docs/architecture/README.md)
- Definition of Done: [`docs/definition-of-done.md`](docs/definition-of-done.md)
- Current handover/transition state: [`docs/customer-handover.md`](docs/customer-handover.md)
