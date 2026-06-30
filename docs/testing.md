# Testing Strategy

This document describes how the AI Sales Manager project is tested, what the critical modules are, and where the tests live.

## Test Philosophy

- Tests are **maintained project assets**: they live in `tests/` and run on every CI build.
- New features and bug fixes must include tests that would fail without the change.
- Quality Requirement Tests (QRTs) are treated as first-class tests and run in CI alongside unit and integration tests.

## Test Stack

- **pytest** — test runner.
- **pytest-asyncio** — async test support.
- **pytest-mock / unittest.mock** — mocking dependencies.
- **pytest-cov** — coverage reporting.
- **FastAPI TestClient** — HTTP-level integration tests.
- **ruff** — linting and formatting checks.
- **bandit** — additional security-focused static analysis.
- **pip-audit** — dependency vulnerability scanning.
- **lychee** — broken-link checking for Markdown files.

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# Quality Requirement Tests only
pytest tests/quality_requirement_tests/ -v
```

## Critical Modules and Coverage

A module is considered **critical** when a bug in it directly impacts customer-facing functionality (API, bots, scheduler), data integrity (models, import), or security/reliability (account management, encryption).

| Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
|---|---|---:|---:|---|
| `app/api/*.py` | REST API endpoints exposed to users and integrations. | ≥ 30% | 72–100% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| `app/core/scheduler.py` | Campaign processing, account selection, anti-spam logic. | ≥ 50% | 80% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| `app/core/state_machine.py` | Conversation state transitions. | ≥ 90% | 100% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| `app/llm/engine.py` | LLM generation and fallback cascade. | ≥ 90% | 94% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| `app/llm/guardrails.py` | Output safety checks. | ≥ 90% | 90% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| `app/services/notification_service.py` | Hot lead alerts. | ≥ 90% | 94% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| `app/bots/seller_client.py` | Telegram MTProto client wrapper. | ≥ 30% | 70% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| `app/services/lead_validation.py` | Contact validation and enrichment. | ≥ 30% | 72% | [CI coverage run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |

## Automated Test Status

| Test type | Scope | Command or CI check | Latest result | Evidence |
|---|---|---|---|---|
| Unit tests | Critical product logic | `pytest tests/test_*.py -v` | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Integration tests | API routes with database and service interaction | `pytest tests/test_api_*.py tests/test_e2e.py -v` | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Automated QRTs | QR-001, QR-002, QR-003 | `pytest tests/quality_requirement_tests/ -v` | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |

## CI and QA Check Status

| Gate or check | Required for Done? | Latest protected-branch status | Evidence |
|---|---|---|---|
| Linting (ruff) | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Formatting check (ruff) | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Unit and integration tests | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Automated QRTs | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Line coverage (≥ 30%) | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Security static analysis (bandit) | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Dependency vulnerability scan (pip-audit) | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) |
| Broken-link check (lychee) | Yes | Passing | [CI run](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/links.yml) |

## Additional QA Check Rationale

| QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations or follow-up |
|---|---|---|---|---|---|
| Common security issues (hardcoded secrets, weak crypto, unsafe deserialization) may expose Telegram session strings, API keys, or encrypted credentials. | Bandit static security analysis. | `app/` Python source code. | Passing (0 findings) | [CI bandit job](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) | Bandit does not replace dependency vulnerability scanning. |
| Dependencies with known vulnerabilities may expose users or deployments to avoidable risk. | `pip-audit` dependency vulnerability scan. | `requirements.txt` and installed packages. | Passing (0 findings) | [CI pip-audit job](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/ci.yml) | Some vulnerabilities may require manual triage or delayed upstream fixes. |
| Broken links in maintained documentation reduce trust and make reports hard to verify. | `lychee` broken-link checker. | All Markdown files, including `docs/` and `reports/`. | Passing | [CI lychee job](https://github.com/Aye-basota/AI-sales-manager/actions/workflows/links.yml) | Excludes rate-limited or unstable external links only when narrowly justified. |

## Manual Evidence That Does Not Count as QRT

| Evidence | Scope | Result | Follow-up PBI or issue |
|---|---|---|---|
| Customer UAT observation | End-to-end campaign creation and execution | To be recorded during Sprint Review | TBD |

## Coverage Reports

Coverage HTML reports are generated in CI and uploaded as artifacts. Local report:

```bash
pytest tests/ -q --cov=app --cov-report=html
open htmlcov/index.html
```

## Assignment 4–5 Quality Gates for Later Work

The following gates remain active for later project work:

- All PRs/MRs and protected-default-branch pushes run linting, formatting checks, tests, coverage, QRTs, Bandit, `pip-audit`, and Lychee.
- Critical modules must maintain at least 30% line coverage.
- New user-visible changes require a `CHANGELOG.md` entry.
- New quality requirements require a linked automated QRT.
- Architecture changes require updated architecture documentation and linked ADRs.

If a later product change makes a gate obsolete, it will be replaced with an equivalent or stronger check and documented here.

## MVP v2 Test Additions

As `MVP v2` features are implemented, extend this section with:

- New critical modules introduced by the Sprint scope.
- New unit and integration tests for changed or new product areas.
- New automated QRTs for any new quality requirements.
- Updated coverage evidence from the latest protected-default-branch CI run.
