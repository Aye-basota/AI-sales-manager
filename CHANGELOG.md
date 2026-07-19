# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Admin Bot now uses an LLM draft audit after business creation to generate
  business-specific owner clarification questions, with a deterministic fallback
  if the audit is unavailable.
- Business creation now lets owners choose custom communication style, custom
  sales-funnel instructions, and whether the AI may ask the owner for missing
  facts during live lead chats.
- Inbound replies can request a business-owner clarification at runtime when a lead asks about unknown prices, delivery, documents, payment terms, samples, address, branding, or assortment.

### Changed
- LLM reply context now includes verified owner-provided business facts and treats unknown operational details conservatively.
- The Admin Bot business wizard now shows "step X of N" labels and explains that
  the follow-up delay controls when the bot writes again if a lead is silent.

### Fixed
- Inbound Telegram replies now resolve duplicate contacts by `telegram_user_id`
  and username, preferring the freshest active campaign so replies do not land in
  stale conversations.
- New campaign launches now skip a cold first message when the same seller
  account has already contacted the same Telegram person in another campaign.
- Re-importing a Telegram contact from CSV now resets stale `invalid_peer` validation state so corrected usernames or ids can be retried in new campaigns.
- Inbound Telegram replies are now serialized per sender to avoid duplicate AI answers when a lead sends quick consecutive messages.
- Short positive replies such as "yes" or "tell me more" now keep the lead warm instead of immediately creating a hot-lead alert.
- First outreach messages now avoid vague offer wording and grammar mistakes around sales/supply scripts.
- Inbound replies now refresh visible Telegram profile names from the sender before hot-lead notifications are composed.
- Pricing, pause, and wrong-recipient replies now use deterministic safe fallbacks instead of premature meeting pushes.
- Unsupported generated claims about business terms are now replaced with an owner-clarification hold message or a safe unknown-fact fallback before Telegram dispatch.
- Urgent or high-volume commercial replies are now treated as hot leads even when the lead has not explicitly asked for a meeting.

## [0.5.0] - 2026-07-17

Final Assignment 6 release candidate mapped to `MVP v3`.

### Added
- Human-like outbound message bursts can now split longer natural replies into short consecutive Telegram messages.
- LLM route audit logs now record prompt route, history size, response source, model, token usage, and chunk count for outbound, follow-up, and inbound replies.

### Changed
- Lead reply prompts and deterministic fallbacks now answer pricing/basic-condition questions before any CTA and repair confusing previous replies instead of repeating them.
- Follow-up prompts now explicitly model a single no-reply nudge with conversation history, last manager message, lead facts, and anti-repetition rules.
- Lead replies and follow-ups now pass recent dialogue to the LLM as real `user`/`assistant` chat messages instead of flattening the whole history into one prompt.
- Dialogue prompts are shorter and prioritize the latest lead message, verified context, and role consistency over long rule lists.
- Approved preview messages from the Admin Bot are now reused for the actual first send instead of regenerating a different first message.

### Fixed
- Contacts who reply before or while a campaign is paused are marked as `replied`, preventing stale initial greetings or follow-ups from being sent later.
- Follow-ups are now skipped after replies, previous follow-ups, operator intervention, escalations, terminal states, or missing conversation context.
- Guardrails and deterministic fallbacks now allow verified product conditions such as minimum order volume while still blocking invented prices, files, catalogs, and product-consulting promises.

### Release
- Updated API metadata to identify the final Assignment 6 `MVP v3` release candidate as version `0.5.0`.

## [0.4.0] - 2026-07-08

### Changed
- Updated API metadata to identify the Week 6 trial release as version `0.4.0`.
- Release automation now verifies that a SemVer tag points to a commit contained in `main` before publishing a GitHub Release.
- Seller MTProto read/typing actions now use Pyrogram chat-level methods instead of raw peers with missing access hashes.

### Fixed
- Prevented release/profile deployments from failing during startup when `DEBUG` is set to values such as `release`, `prod`, or `production`.
- Prevented copied `.env.example` values such as an empty `TELEGRAM_API_ID` or placeholder `ADMIN_BOT_TOKEN` from breaking API startup.
- Inbound Telegram auto-replies now respect seller-account daily and 30-second rate limits and update account counters after sending.
- Guardrails now correctly detect emoji/symbol categories through Unicode metadata.

### Security
- Telegram account API responses no longer expose stored `session_string` values.

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
