# Customer Handover

This page describes the **current actual** handover state of AI Sales Manager. It is updated during Week 6 and Week 7 of Assignment 6 as the transition progresses — it does not describe an aspirational future state.

**Status as of this update:** Sprint 5 (Week 7) follow-up maintenance has resolved the customer's outstanding Week 6 feedback (lead-discovery quality and prompt/response quality). The final `MVP v5` , the previous trial tag was `v0.4.0` .The final public access arrangement for course evaluation is the Telegram Admin Bot at [@salesmanager228_bot](https://t.me/salesmanager228_bot), backed by the team-operated deployment, plus the reproducible Docker setup in [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md).

**Reached handover level:** `Independently used by customer`. The customer tested the product independently, on his own time, without the team present — admin panel, his own test contacts, a live conversation with the bot, lead search, and the analytics dashboard.

**Customer-confirmation status:** `Accepted`. On the Week 7 call, the customer confirmed acceptance of the current product and documentation state. His two Week 6 follow-up items — lead-search/parsing quality and overall prompt/response quality — were independently re-tested by him during the Week 7 call and confirmed resolved. No further follow-up items were raised.

---

## What This Page Covers

- What was transferred, delegated, or retained by the team
- What the customer needs to know about configuration and external services (without exposing secrets)
- How to set up, deploy, recover, and verify the product
- Where to go for normal use, operation, and troubleshooting
- What remains as optional follow-up beyond the reached handover level

For step-by-step setup instructions, use [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md) alongside this page — this document explains *what* the handover looks like, `LAUNCH_GUIDE.md` explains *how* to execute it.

---

## Repository, Service, and Account Ownership

| Item | Current arrangement |
|---|---|
| **Source code repository** | Public on GitHub at [`Aye-basota/AI-sales-manager`](https://github.com/Aye-basota/AI-sales-manager), owned by the team for course delivery. The customer can read, clone, and fork it from the public repository. |
| **Hosted documentation site** | GitHub Pages at [aye-basota.github.io/AI-sales-manager](https://aye-basota.github.io/AI-sales-manager/), built from this repository. Public and readable by anyone; no separate account or transfer is needed to use it. |
| **Running product instance** | Final `MVP v3` access for customer/TA evaluation is the Telegram Admin Bot / live bot instance: [@salesmanager228_bot](https://t.me/salesmanager228_bot). The team keeps this access artifact available until grading is complete. |
| **Telegram seller account** | The live Telegram account used to send messages belongs to whoever supplies the phone number during setup. The course evaluation instance uses a team-controlled test number; customer-owned seller numbers are supported through the same setup flow. |
| **LLM provider account (OpenRouter / DashScope)** | LLM access is configured through environment variables. The course evaluation instance uses team-managed keys; a customer-run instance can provide customer-owned keys without code changes. |
| **Admin Telegram Bot** | Registered via BotFather under the course evaluation bot token and used as the main `MVP v3` entry point. A customer-owned bot token can be configured through the same `.env` setup path. |

**Summary:** the customer has independently used final `MVP v3` through the public Telegram bot and reproducible Docker setup. The course evaluation arrangement keeps the live instance team-operated while making the repository, documentation, and configuration path available for customer-side operation when the customer chooses to move to it.

---

## Configuration, External Services, and Secrets

The product is configured entirely through environment variables, never through values committed to the repository. `.env.example` in the repository root lists every variable name the customer will need to fill in; the actual `.env` file must never be committed (it is already `.gitignore`d).

For a customer-run instance, the customer needs the following categories of value. They are configured through environment variables and are never committed to the repository:

| Category | What it's for | Where to get it |
|---|---|---|
| Telegram API ID / API Hash | Lets the product send messages as a real Telegram user account (MTProto) | [my.telegram.org](https://my.telegram.org), tied to the seller phone number |
| Telegram Admin Bot token | Controls the product through Telegram (campaigns, contacts, analytics) | [@BotFather](https://t.me/BotFather) |
| LLM provider API key | Generates conversational replies (OpenRouter or DashScope) | [openrouter.ai/keys](https://openrouter.ai/keys) or [dashscope-intl.aliyuncs.com](https://dashscope-intl.aliyuncs.com) |
| `SESSION_ENCRYPTION_KEY` | A Fernet key used to encrypt the stored Telegram session string in the database | Generated once locally (see `LAUNCH_GUIDE.md`) and kept secret |
| `SECRET_KEY` | Application-level secret (JWT/crypto) | Set to a random value before any non-local deployment; the default `changeme` must not be used in production |
| Database / Redis connection strings | PostgreSQL and Redis, provisioned by Docker Compose by default | Only needs manual values if hosting on managed infrastructure instead of the bundled containers |

Each side that runs the product supplies its own secrets for the environment it operates.

---

## Deployment and Access

- **Local / demo deployment:** `docker-compose up -d --build` followed by `docker-compose exec api alembic upgrade head`. Full walkthrough in [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md).
- **Final MVP v3 entry point:** Telegram Admin Bot backed by a team-controlled live instance: [@salesmanager228_bot](https://t.me/salesmanager228_bot).
- **Temporary public web/API access:** the team can expose a running API/site instance publicly using `docker-compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d`, which opens a [localtunnel](https://theboroer.github.io/localtunnel-www/) HTTPS URL. This URL is **ephemeral** and must be recorded separately for each trial if used.
- **Persistent production hosting:** the final public handover level uses a team-operated bot/deployment for course evaluation and documented Docker-based self-hosting for reproduction. The customer has indicated he plans to move to his own infrastructure at a later date, outside the scope of this course; customer-owned deployment can use the same Docker and environment-variable setup.
- **Recovery:** the documented recovery path is to run `alembic upgrade head` against a fresh database and re-add Telegram accounts and scripts. A fuller backup/restore runbook is a follow-up item for customer-owned operation.
- **Verification after setup:** `GET /health` returns `status`, `db`, and `scheduler` — use it to confirm the API, database, and background scheduler all came up correctly. The maintained test suite covers 459 automated tests with ≥80% coverage on `app/`.

---

## Main Documentation Entry Points

| Need | Document |
|---|---|
| First-time orientation to the product | [`README.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/README.md) |
| Step-by-step non-technical setup | [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md) |
| This handover page | `docs/customer-handover.md` (this file) |
| Contributing changes to the code | [`CONTRIBUTING.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/CONTRIBUTING.md) |
| Guidance for AI coding agents working in this repo | [`AGENTS.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/AGENTS.md) |
| What has been verified with the customer | [`docs/user-acceptance-tests.md`](user-acceptance-tests.md) |
| Known issues and limitations | [`README.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/README.md) and [`CHANGELOG.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/CHANGELOG.md) |
| Architecture and how the system is built | [`docs/architecture/README.md`](architecture/README.md) |
| Full documentation, browsable | [Hosted documentation site](https://aye-basota.github.io/AI-sales-manager/) |

---

## Troubleshooting and Support

- **Setup problems (Docker not starting, session-string generation stuck, etc.):** `LAUNCH_GUIDE.md` includes an "Если не сработало" (*"If it didn't work"*) callout after the Docker install step and after the session-string generation step — check those first.
- **Runtime health check:** `GET /health` reports `status`, `db`, and `scheduler` separately, so a failing check tells you which component is down.
- **Known, already-diagnosed issues:** see [`README.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/README.md) for the current list of known limitations and fixed risks, including inbound rate-limit handling and the remaining low-probability double-reply race condition.
- **Anything else:** use the public repository issues or the agreed team communication channel for support during the course evaluation and transition period.

---

## Transition Status

Using the terminology defined for Assignment 6 Part 8:

- **Reached handover level:** `Independently used by customer`.
- **Customer-confirmation status:** `Accepted`.
- **Final product access artifact:** [@salesmanager228_bot](https://t.me/salesmanager228_bot), backed by the team-operated deployment.
- **Repository and documentation access:** public GitHub repository plus hosted documentation site.
- **Customer-side operation path:** supported through the Docker setup and customer-provided Telegram/LLM credentials; the customer has indicated he plans to move to this at a later date.

This means the product has been independently tested and accepted by the customer, with no outstanding follow-up items raised on the Week 7 call.

---

## Is the Current Documentation Sufficient?

**Sufficient for the reached handover level (`Independently used by customer`).** The documentation set (`README.md`, `LAUNCH_GUIDE.md`, this page) was enough for the customer to independently test the product end-to-end. On the Week 7 call, the customer noted the handover documentation was not fully clear on first read, without specifying the exact section — this is logged as an open item for the team to follow up on directly with the customer, separate from the overall `Accepted` transition status.

Remaining optional follow-up items for a stronger customer-owned operation model:

- Provisioning a persistent customer-owned hosting environment.
- Generating and rotating the Telegram session string (`scripts/generate_session.py` requires an interactive SMS code step).
- Expanding the backup/restore runbook beyond the current fresh-database recovery path.
- Identifying and clarifying the specific part of this document the customer found unclear.

These are optional improvements beyond the reached handover level, not blockers to the `Accepted` transition status.
