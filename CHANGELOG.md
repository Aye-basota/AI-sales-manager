# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-06-30

### Added
- MVP v2 lead-nurturing funnel stages: trust → engagement → qualification → value → CTA.
- External prompt configuration and versioning in `app/config/prompts/v1.json` (TECH-13).
- Funnel upload/preview API with JSON and plain-text parsers: `POST /api/funnels/preview`, `POST /api/funnels/upload` (TECH-04, TECH-05).
- `Funnel` model and Alembic migration `20260630_mvp_v2_funnel_and_automation.py`.
- AI-automation rate tracking: `Conversation.was_escalated` flag and `GET /analytics/automation-rate` (TECH-06).
- Production observability: structured logging via `LOG_LEVEL`, `/health` endpoint, and Docker Compose health checks/restart policies (TECH-12).
- MkDocs Material documentation site under `docs/` and `.github/workflows/docs.yml`.
- `pip-audit` dependency vulnerability scan in CI.
- `lychee` link checker in CI.

### Changed
- Default funnel prompts now emphasize trust building, natural dialogue, and value-before-CTA (US-017, US-018).
- Conversation stage progression uses legacy alias mapping (`hook` → `trust`) for backward compatibility.
- `app/config.py` refactored into `app/config/` package to separate settings from prompt configs.
- Dependency updates for security: FastAPI 0.138.2, Starlette 1.3.1, Pydantic 2.13.4, Pydantic-Settings 2.14.2.

### Fixed
- Funnel preview response now allows `created_at: null` for non-persisted previews.

## [0.2.0] - 2026-06-27

### Added
- Automated Quality Requirement Tests (QRTs) in `tests/quality_requirement_tests/`:
  - QRT-001: health endpoint latency (95th percentile ≤ 500 ms).
  - QRT-002: health endpoint availability proxy.
  - QRT-003: API fault tolerance on invalid JSON.
- `docs/quality-requirement-tests.md` linking QRTs to quality requirements.
- `docs/testing.md` documenting testing strategy, critical modules, and coverage thresholds.
- Additional CI QA check: `bandit` security static analysis.
- Seed demo data script `scripts/seed_demo_data.py` for presentations.
- Localtunnel support for public access: `scripts/start_localtunnel.sh` and `docker-compose.tunnel.yml`.
- Exception handler returning HTTP 400 Bad Request for invalid request payloads.

### Changed
- Health endpoint now reports `degraded` when the scheduler is not running.
- `processed_contacts` now counts unique contacts rather than outbound messages.
- `README.md` testing section now references QRTs and current coverage.
- CI workflow runs tests with coverage reporting and uploads `htmlcov` artifacts.

### Fixed
- Inbound analytics (`replied_count`, `CampaignContact.status`) are no longer updated for paused/closed campaigns.
- Assigned account selection now validates eligibility (status, session string, cooldown) and falls back to any eligible account.

## [0.1.0] - 2026-06-19

### Added
- MVP v1: configurable multi-stage sales funnel (hook → qualification → value → CTA).
- `Script.sales_funnel`, `first_message_goal`, `call_to_action`, `language`, `emoji_policy`, `max_first_message_length` fields.
- `Conversation.conversation_stage` tracked through the funnel.
- Funnel-aware prompt generation in `app/llm/prompts.py`.
- Funnel stage progression integrated into inbound listener and outbound scheduler.
- Admin bot support for `first_message_goal` selection during `/newscript`.
- Alembic migration `20260615_funnel_fields.py` for funnel columns.
- Unit tests for funnel logic and funnel-aware prompts.
- GitHub issue templates (User Story, Other PBI, Course Task, Bug Report).
- Extended pull request template.
- Week 3 report structure under `reports/week3/`.

### Changed
- `ScriptCreate`/`ScriptUpdate` schemas: `sales_funnel` is now a list of stage objects.

### Fixed
- Funnel schema type mismatch between API and core logic.
