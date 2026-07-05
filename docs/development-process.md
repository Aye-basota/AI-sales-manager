# Development Process and Configuration Management

## Overview

This document describes the team's actual development workflow, board configuration, branching strategy, configuration management, CI process, and release process for the AI Sales Manager project.

---

## Boards and Views

The team uses **GitHub Projects** to manage the Product Backlog and Sprint Backlog.

| Board | URL | Purpose |
|---|---|---|
| Product Backlog | [GitHub Projects — Backlog](https://github.com/users/Aye-basota/projects/1/views/1) | All active PBIs ordered by MoSCoW priority |
| Sprint Backlog | [GitHub Projects — Sprint Board](https://github.com/users/Aye-basota/projects/2) | Issues assigned to the current Sprint milestone, shown as a Kanban board |

The Sprint Backlog board columns map directly to Work Status values:

| Column | Work Status | Entry Criteria |
|---|---|---|
| To Do | `status:to-do` | Issue assigned to Sprint milestone, has acceptance criteria and SP |
| In Progress | `status:in-progress` | Developer has started implementation; branch exists and is linked to the issue |
| Review | `status:review` | PR is open and linked to the issue; at least one reviewer assigned |
| Done | `status:done` | PR is merged, all acceptance criteria verified, CI passes, DoD satisfied |

---

## Git Workflow

The team follows a **feature-branch workflow** with a protected `main` branch and mandatory PR review before merge.

### Branch Naming Convention

Every feature branch is linked to a GitHub Issue:

```
<issue-number>-short-description
```

Examples:
- `3-getting-product-info`
- `17-launch-outreach-campaign`
- `45-operator-takeover`

### Workflow Steps

1. Create a GitHub Issue for the PBI or task.
2. Assign the issue to the current Sprint milestone.
3. Create a branch from `main` named `<issue-number>-short-description`.
4. Commit changes on the feature branch (small, focused commits).
5. Open a Pull Request that references the issue (`closes #N`).
6. At least one other team member reviews and approves the PR.
7. All CI checks must pass before merge.
8. Merge into `main` using a **merge commit** (no squash, no rebase) to preserve full history.
9. GitHub automatically closes the linked issue on merge.
10. Delete the feature branch after merge.
11. Tag `main` with a SemVer release when a Sprint increment is complete.

### How Issues Are Used

- Every PBI, bug, task, and documentation item has a GitHub Issue.
- Issues contain: stable ID in the title, user-story statement or description, acceptance criteria, MoSCoW label, SP label, type label, Work Status label, assignee, and reviewer.
- Issues are closed automatically when the linked PR is merged to `main`.

### How PRs Are Reviewed

- The PR author links the issue in the PR description (`closes #N`).
- The PR description lists the acceptance criteria and confirms each is satisfied.
- At least one reviewer approves before merge.
- The reviewer leaves at least one meaningful comment confirming the verification.

---

## Git Workflow Diagram

```mermaid
gitGraph
   commit id: "Initial project setup"
   commit id: "v0.1.0 — MVP v1" tag: "v0.1.0"

   branch 3-getting-product-info
   checkout 3-getting-product-info
   commit id: "Implement US-01 core logic"
   commit id: "Add unit tests for US-01"
   checkout main
   merge 3-getting-product-info id: "Merge PR: US-01 done"

   branch 5-bot-setup-funnel
   checkout 5-bot-setup-funnel
   commit id: "Implement US-03 funnel upload"
   commit id: "Add acceptance criteria tests"
   checkout main
   merge 5-bot-setup-funnel id: "Merge PR: US-03 done"

   branch 17-launch-outreach-campaign
   checkout 17-launch-outreach-campaign
   commit id: "Implement US-012 campaign launch"
   commit id: "Integration tests for campaign"
   checkout main
   merge 17-launch-outreach-campaign id: "Merge PR: US-012 done"

   branch 45-operator-takeover
   checkout 45-operator-takeover
   commit id: "Add is_paused_by_operator flag"
   commit id: "Operator API endpoints"
   commit id: "Tests for takeover flow"
   checkout main
   merge 45-operator-takeover id: "Merge PR: operator takeover"

   branch 46-rate-limiting
   checkout 46-rate-limiting
   commit id: "Inbound rate limiter"
   commit id: "Daily limit guard per account"
   checkout main
   merge 46-rate-limiting id: "Merge PR: rate limiting"

   commit id: "v0.2.0 — MVP v2" tag: "v0.2.0"
```

### What the Diagram Shows

- **`main`** is the protected default branch. Only merge commits from reviewed PRs land here. Direct pushes to `main` are blocked.
- **Feature branches** are short-lived. Each branch maps to one GitHub Issue (e.g., `3-getting-product-info` → Issue #3).
- **SemVer tags** (`v0.1.0`, `v0.2.0`) mark Sprint release points on `main`. Tags correspond to MVP milestones.
- **Parallel branches** (`45-operator-takeover`, `46-rate-limiting`) show concurrent work on separate issues without blocking each other.
- **Merge commits** preserve the full commit history of each branch, making traceability from commit → branch → issue → PR complete and auditable.

---

## Configuration and Secrets Management

### Environment Variables

All runtime secrets and environment-specific values are supplied via environment variables — **never committed to the repository**.

| Variable | Purpose |
|---|---|
| `TELEGRAM_API_ID` | MTProto API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | MTProto API Hash |
| `OPENROUTER_API_KEY` | OpenRouter LLM provider key |
| `DASHSCOPE_API_KEY` | DashScope (Qwen) LLM provider key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string (for session locks and rate limiting) |
| `ADMIN_BOT_TOKEN` | Telegram Bot token for the Admin Bot |

### `.env.example`

A committed `.env.example` file documents all required variable names with empty placeholder values. The actual `.env` file is listed in `.gitignore` and must never be committed.

### `.gitignore` Baseline

The following are always excluded from the repository:

- `.env` (runtime secrets)
- `*.session` (Telegram MTProto session files — grant account access)
- `__pycache__/`, `*.pyc`
- `*.pem`, `*.key`
- Local Docker volumes

### Docker Runtime Configuration

`docker-compose.yml` reads all secrets from environment variables at runtime. No secrets are baked into Docker images. A `Dockerfile.backend` and `Dockerfile.frontend` are committed for reproducible builds using only public base images and pinned dependency versions.

---

## Reproducible Development Environment

The team uses a **Python virtual environment + Docker Compose** setup.

### Local Setup (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values
python -m pytest
```

### Docker Setup

```bash
cp .env.example .env   # fill in real values
docker compose up --build
```

The backend is available at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

All team members use the same `requirements.txt` for dependency pinning. No environment-specific setup scripts are required beyond the above steps.

---

## CI Process

The team currently runs all automated checks locally. GitHub Actions CI is planned for Sprint 4.

| Check | Command | When Run |
|---|---|---|
| Unit and integration tests | `python -m pytest` | Before every PR |
| Type checking | `mypy .` | Before every PR |
| Linting | `ruff check .` | Before every PR |

Once GitHub Actions is configured (Sprint 4), these checks will run automatically on every PR and on every push to `main`. Branch protection rules will require CI to pass before merge.

---

## Definition of Done Enforcement

A PBI may only be merged to `main` when:

- All acceptance criteria are satisfied and confirmed in the PR description.
- At least one team member has reviewed and approved the PR.
- All local tests pass (`pytest`, `mypy`, `ruff`).
- `CHANGELOG.md` is updated for any user-visible change.
- `docs/` files are updated if the change affects architecture, process, or user-facing behavior.
- No secrets or PII appear in the commit.

See [`docs/definition-of-done.md`](definition-of-done.md) for the full DoD checklist.

---

## Release Process

1. Complete all Sprint PBIs and verify the Definition of Done for each.
2. Update `CHANGELOG.md` under the new version heading.
3. Merge the last Sprint PR to `main`.
4. Create a GitHub Release with a SemVer tag (`vX.Y.Z`) pointing to the merge commit on `main`.
5. The release description links: Sprint milestone, public Week N report, demo video, and run instructions.

See [`CHANGELOG.md`](../CHANGELOG.md) for the release history.

---

## Links

- [Root README.md](../README.md)
- [Definition of Done](definition-of-done.md)
- [Roadmap](roadmap.md)
- [Architecture](architecture/README.md)
- [Week 5 Report](../reports/week5/README.md)
