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
- **bandit** — additional security-focused static analysis.

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# Quality Requirement Tests only
pytest tests/quality_requirement_tests/ -v
```

## Critical Modules

A module is considered **critical** when a bug in it directly impacts:

- customer-facing functionality (API, bots, scheduler),
- data integrity (models, import),
- security or reliability (account management, encryption).

| Module | Responsibility | Coverage Threshold |
|---|---|---|
| `app/api/*.py` | REST API endpoints | ≥ 30% |
| `app/core/scheduler.py` | Campaign processing and anti-spam logic | ≥ 50% |
| `app/core/state_machine.py` | Conversation state transitions | ≥ 90% |
| `app/llm/engine.py` | LLM generation and fallback cascade | ≥ 90% |
| `app/llm/guardrails.py` | Output safety checks | ≥ 90% |
| `app/services/notification_service.py` | Hot lead alerts | ≥ 90% |
| `app/bots/seller_client.py` | Telegram MTProto client wrapper | ≥ 30% |
| `app/services/lead_validation.py` | Contact validation and enrichment | ≥ 30% |

## Test Locations

- Unit tests: `tests/test_*.py`.
- Integration tests: `tests/test_api_*.py`, `tests/test_e2e.py`.
- Quality Requirement Tests: `tests/quality_requirement_tests/`.

## Additional QA Check

- **Tool:** `bandit`.
- **Objective:** Detect common security issues in Python code (e.g., weak cryptography, hardcoded passwords, unsafe deserialization).
- **Why it matters:** The product handles Telegram session strings, API keys, and encrypted credentials. Bandit helps catch accidental security regressions.
- **CI job:** `.github/workflows/ci.yml` job `bandit`.

## Coverage Reports

Coverage HTML reports are generated in CI and uploaded as artifacts. Local report:

```bash
pytest tests/ -q --cov=app --cov-report=html
open htmlcov/index.html
```
