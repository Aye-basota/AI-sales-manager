# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- DashScope (Alibaba Cloud) LLM provider support via `LLM_PROVIDER=dashscope`.
- Configurable `DASHSCOPE_API_KEY` and `DASHSCOPE_BASE_URL` environment variables.

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
