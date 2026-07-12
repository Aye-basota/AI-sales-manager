# Testing Strategy — AI Sales Manager

## Overview

The project uses **pytest** for all automated testing. Tests are organized by module in `tests/`.
As of the latest QA audit, the suite contains **708 tests**. Application code coverage is approximately **82%** for `app/`; coverage is **81%** when manual utility scripts in `scripts/` are included.

Run the full suite:
```bash
pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=75
```

---

## Test Categories

### Unit Tests

Unit tests cover isolated business logic with mocked dependencies.

| File | Module | What it tests |
|---|---|---|
| [`tests/test_core_state_machine.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_core_state_machine.py) | `app/core/state_machine.py` | All state transitions, terminal state immutability, unknown event handling |
| [`tests/test_llm_guardrails.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_llm_guardrails.py) | `app/llm/guardrails.py` | Length check, forbidden topics, anti-repetition, bot-word detection, markdown detection |
| [`tests/test_core_humanizer.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_core_humanizer.py) | `app/core/humanizer.py` | Typing delays, message chunking, markdown stripping, casual marker injection |
| [`tests/test_llm_engine.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_llm_engine.py) | `app/llm/engine.py` | LLM cascade fallback, retry logic, hardcoded fallback |
| [`tests/test_llm_intent_classifier.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_llm_intent_classifier.py) | `app/llm/intent_classifier.py` | Intent classification outputs |
| [`tests/test_llm_prompts.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_llm_prompts.py) | `app/llm/prompts.py` | Prompt template rendering |
| [`tests/test_llm_funnel_prompts.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_llm_funnel_prompts.py) | `app/llm/prompts.py` + `app/core/funnel.py` | Stage-aware prompt generation |
| [`tests/test_core_funnel.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_core_funnel.py) | `app/core/funnel.py` | Stage progression, aliases, CTA rules |
| [`tests/test_core_account_manager.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_core_account_manager.py) | `app/core/account_manager.py` | Account selection, cooldown logic, daily limit enforcement |
| [`tests/test_db_redis.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_db_redis.py) | `app/db/redis.py` | Redis cache read/write/invalidation |

### Integration Tests

Integration tests verify interactions between components using `AsyncMock` for external services.

| File | Components covered |
|---|---|
| [`tests/test_core_scheduler.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_core_scheduler.py) | Scheduler ↔ Account Manager ↔ LLM Engine ↔ DB |
| [`tests/test_bots_inbound_listener.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_bots_inbound_listener.py) | Inbound Listener ↔ Conversation Service ↔ LLM Engine |
| [`tests/test_bots_seller_client.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_bots_seller_client.py) | SellerClient ↔ Pyrogram (mocked) |
| [`tests/test_services_conversation_service.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_services_conversation_service.py) | Conversation Service ↔ DB ↔ Redis |
| [`tests/test_services_contact_import.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_services_contact_import.py) | CSV/Excel import ↔ DB |
| [`tests/test_humanizer_integration.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_humanizer_integration.py) | Humanizer ↔ SellerClient (typing simulation) |
| [`tests/test_api_campaigns.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_api_campaigns.py) | FastAPI campaign endpoints ↔ DB |
| [`tests/test_api_conversations.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_api_conversations.py) | FastAPI conversation endpoints ↔ DB |
| [`tests/test_api_funnels.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_api_funnels.py) | FastAPI funnel preview/upload endpoints ↔ parser ↔ DB |
| [`tests/test_api_analytics.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_api_analytics.py) | FastAPI analytics endpoints (automation-rate) ↔ DB |

### End-to-End Tests

| File | What it covers |
|---|---|
| [`tests/test_e2e.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_e2e.py) | Full campaign cycle: import → schedule → send → inbound reply → state transition → notification |

### Scenario / Regression Tests

| File | Risk addressed |
|---|---|
| [`tests/test_flood_wait.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_flood_wait.py) | Pyrogram FloodWait handling and account cooldown |
| [`tests/test_timezone.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_timezone.py) | Working hours filter with different timezones |
| [`tests/test_deduplication.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_deduplication.py) | Duplicate contact prevention during import |
| [`tests/test_auto_close.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_auto_close.py) | 48 h auto-close when lead does not reply |
| [`tests/test_daily_reset.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_daily_reset.py) | Daily message counter reset at 00:00 MSK |
| [`tests/test_inbound_fallback.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_inbound_fallback.py) | LLM failure fallback to hardcoded Russian message |
| [`tests/test_validation.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_validation.py) | Contact validation (phone/username format) |
| [`tests/test_facts_extraction.py`](https://github.com/Aye-basota/AI-sales-manager/blob/main/tests/test_facts_extraction.py) | LLM-extracted facts stored in conversation |

---

## Critical Modules and Coverage

| Module | Coverage | Threshold | Status |
|---|---|---|---|
| `app/api/campaigns.py` | ~100% | Covered by API tests | ✅ |
| `app/api/contacts.py` | ~97% | Covered by API and discovery tests | ✅ |
| `app/core/account_manager.py` | ~100% | Covered by unit and DB-helper tests | ✅ |
| `app/db/redis.py` | ~100% | Covered by cache lifecycle tests | ✅ |
| `app/services/conversation_service.py` | ~100% | Covered by DB, cache, and fact tests | ✅ |
| `app/services/contact_import.py` | ~98% | Covered by CSV/Excel parsing tests | ✅ |
| `app/services/funnel_parser.py` | ~98% | Covered by direct parser and API tests | ✅ |
| `app/services/lead_discovery.py` | ~95% | Covered with mocked adapters/clients | ✅ |
| `app/services/lead_validation.py` | ~92% | Covered with mocked Pyrogram clients | ✅ |
| `app/services/tgstat_lead_search.py` | ~91% | Covered with mocked TGStat and Telegram clients | ✅ |
| `app/bots/admin_bot.py` | ~64% | Large Telegram UI surface remains the biggest gap | ⚠️ |
| `app/core/scheduler.py` | ~80% | Remaining misses are mostly rare failure/recovery branches | ⚠️ |
| **Global `app/`** | **~82%** | CI gate: ≥ 75% | ✅ |

The CI coverage gate is intentionally below the current `app/` coverage so routine refactors have a small buffer, but high enough to catch major untested additions. Manual scripts under `scripts/` are audited separately because several require live credentials, local files, or operator interaction.

---

## Additional QA Check: Static Security Analysis with Bandit

### Options Considered

| Tool | Purpose | Decision |
|---|---|---|
| `bandit` | Python security linter — detects hardcoded secrets, SQL injection, unsafe subprocess calls | **Selected** |
| `pip-audit` | Checks dependencies for known CVEs | **Selected** |
| `lychee` | Broken-link checker for Markdown files | **Selected** |
| `radon` | Cyclomatic complexity — flags overly complex functions | Deferred (not a security risk) |
| `pylint` | General code quality | Not selected — overlaps with existing `flake8` linting |

### Selected Check: Bandit Security Analysis

**QA objective:** Detect Python security anti-patterns introduced during development — hardcoded secrets, use of `eval()`, unsafe `subprocess` calls, and insecure hash functions.

**Why this matters:** The system handles Telegram session strings (sensitive credentials) and executes scheduled tasks. A developer accidentally hardcoding an API key or using `eval()` on LLM output could expose accounts or allow remote code execution.

**Where it runs in CI:** Runs as a separate `security` job in [`.github/workflows/ci.yml`](https://github.com/Aye-basota/AI-sales-manager/blob/main/.github/workflows/ci.yml), independent of the test job so a security finding does not block coverage reporting.

```bash
bandit -r app/ -ll --format txt
```

The `-ll` flag reports only medium and high severity issues to avoid noise from low-severity style warnings.

**Important limitations:**
- Bandit is a static analyzer — it does not detect runtime injection via LLM output.
- Some `subprocess` calls in `scripts/` are legitimate; these are suppressed with `# nosec` comments where reviewed and intentional.

### Selected Check: Dependency Vulnerability Scan with pip-audit

**QA objective:** Detect known vulnerabilities in Python dependencies before they reach production.

**Why this matters:** The product relies on external packages for Telegram access, LLM calls, and web framework functionality. A vulnerable dependency could expose session strings or API keys.

**Where it runs in CI:** Runs as a separate `pip-audit` job in [`.github/workflows/ci.yml`](https://github.com/Aye-basota/AI-sales-manager/blob/main/.github/workflows/ci.yml).

```bash
pip-audit --requirement requirements.txt --desc
```

### Selected Check: Broken-Link Check with lychee

**QA objective:** Keep documentation and report links valid.

**Why this matters:** Broken links in reports, README, or documentation make the project hard to inspect and reduce trust during grading.

**Where it runs in CI:** Runs in [`.github/workflows/links.yml`](https://github.com/Aye-basota/AI-sales-manager/blob/main/.github/workflows/links.yml) on every push and PR.

```bash
lychee .
```

---

## Adapted Testing Strategy for LLM-Heavy Components

The LLM engine (`app/llm/engine.py`) cannot be tested against real API calls in CI because:
- API keys are not available in CI.
- LLM outputs are non-deterministic.

**Approach:** All LLM calls are mocked with `AsyncMock` returning deterministic fixture responses. Tests verify the orchestration logic (retry, fallback cascade, guardrails integration) rather than LLM output quality. Manual prompt quality review is performed separately during Sprint Reviews.

---

## Running Tests Locally

```bash
# Full suite with coverage
pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=75

# Only unit tests (fast)
pytest tests/test_core_state_machine.py tests/test_llm_guardrails.py tests/test_core_humanizer.py tests/test_llm_engine.py -v

# Only integration tests
pytest tests/test_core_scheduler.py tests/test_bots_inbound_listener.py tests/test_services_conversation_service.py -v

# Security check
bandit -r app/ -ll --format txt
```

---

## Test Maintenance Policy

Tests added during Assignment 4 are maintained product assets. Later project work must:
- Keep all existing tests passing after code changes, or
- Replace removed tests with documented equivalent or stronger coverage when the product feature changes.

Disabling or deleting tests without replacement is not permitted unless the tested module is also removed.
