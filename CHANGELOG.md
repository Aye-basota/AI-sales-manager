# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-27

### Added
- Automated Quality Requirement Tests (QRTs) in `tests/quality_requirement_tests/`:
  - QRT-01: health endpoint latency (95th percentile ≤ 500 ms).
  - QRT-02: health endpoint availability proxy.
  - QRT-03: API fault tolerance on invalid JSON.
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
