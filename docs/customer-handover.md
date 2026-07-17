# Customer Handover

This page describes the **current actual** handover state of AI Sales Manager. It is updated during Week 6 and Week 7 of Assignment 6 as the transition progresses — it does not describe an aspirational future state.

**Status as of this update:** Sprint 5 (Week 7) follow-up maintenance has produced the final Assignment 6 `MVP v3` release candidate. The final public access arrangement for course evaluation is the Telegram Admin Bot at [@salesmanager228_bot](https://t.me/salesmanager228_bot), backed by the team-operated deployment, plus the reproducible Docker setup in [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md).

**Reached handover level:** `Ready for independent use`.

**Customer-confirmation status:** `Not yet accepted` until the Week 7 written confirmation/request evidence is collected in the private submission channel. The stronger levels `Independently used by customer` and `Deployed or operated on customer side` are not claimed in the public repository because customer-side operation has not been publicly evidenced.

---

## What This Page Covers

- What was transferred, delegated, or retained by the team
- What the customer needs to know about configuration and external services (without exposing secrets)
- How to set up, deploy, recover, and verify the product
- Where to go for normal use, operation, and troubleshooting
- What is still missing before the customer can run the product independently

For step-by-step setup instructions, use [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md) alongside this page — this document explains *what* the handover looks like, `LAUNCH_GUIDE.md` explains *how* to execute it.

---

## Repository, Service, and Account Ownership

| Item | Current arrangement |
|---|---|
| **Source code repository** | Public on GitHub at [`Aye-basota/AI-sales-manager`](https://github.com/Aye-basota/AI-sales-manager), owned by the team. **Not yet transferred** to a customer-owned account or organization. The customer can read, clone, and fork it like any public visitor, but does not currently have write or admin access. |
| **Hosted documentation site** | GitHub Pages at [aye-basota.github.io/AI-sales-manager](https://aye-basota.github.io/AI-sales-manager/), built from this repository. Public and readable by anyone; no separate account or transfer is needed to use it. |
| **Running product instance** | Final `MVP v3` access for customer/TA evaluation is the Telegram Admin Bot / live bot instance: [@salesmanager228_bot](https://t.me/salesmanager228_bot). The team keeps this access artifact available until grading is complete. Nothing is claimed as deployed to infrastructure owned by the customer. |
| **Telegram seller account** | The live Telegram account used to send messages belongs to whoever supplies the phone number during setup (currently a team-controlled test number). A production handover requires the customer to either supply their own seller phone number or explicitly authorize continued use of the team's number. |
| **LLM provider account (OpenRouter / DashScope)** | Team-controlled test API keys are used during development. No customer-owned LLM API key has been provisioned yet. |
| **Admin Telegram Bot** | Registered via BotFather under a team-controlled bot token. This is the main Week 6 product entry point for customer interaction. It has not yet been re-registered under a customer-controlled bot account. |

**Summary:** for final `MVP v3`, the team still retains operational control of the GitHub repository, live bot deployment, and external service accounts. The transition level reached is therefore **Ready for independent use**, not customer-side operation. A customer can use the public bot access path and can reproduce the deployment from the repository, but ownership transfer of accounts/infrastructure has not been publicly evidenced.

---

## Configuration, External Services, and Secrets

The product is configured entirely through environment variables, never through values committed to the repository. `.env.example` in the repository root lists every variable name the customer will need to fill in; the actual `.env` file must never be committed (it is already `.gitignore`d).

The customer needs to obtain and hold onto, on their own side, the following categories of value — **none of these are stored in the repository and the team does not have permanent custody of a "production" version of them**:

| Category | What it's for | Where to get it |
|---|---|---|
| Telegram API ID / API Hash | Lets the product send messages as a real Telegram user account (MTProto) | [my.telegram.org](https://my.telegram.org), tied to the seller phone number |
| Telegram Admin Bot token | Controls the product through Telegram (campaigns, contacts, analytics) | [@BotFather](https://t.me/BotFather) |
| LLM provider API key | Generates conversational replies (OpenRouter or DashScope) | [openrouter.ai/keys](https://openrouter.ai/keys) or [dashscope-intl.aliyuncs.com](https://dashscope-intl.aliyuncs.com) |
| `SESSION_ENCRYPTION_KEY` | A Fernet key used to encrypt the stored Telegram session string in the database | Generated once locally (see `LAUNCH_GUIDE.md`) and kept secret |
| `SECRET_KEY` | Application-level secret (JWT/crypto) | Set to a random value before any non-local deployment; the default `changeme` must not be used in production |
| Database / Redis connection strings | PostgreSQL and Redis, provisioned by Docker Compose by default | Only needs manual values if hosting on managed infrastructure instead of the bundled containers |

None of the above are shared secrets between the team and the customer today — each side that runs the product needs to supply its own.

---

## Deployment and Access

- **Local / demo deployment:** `docker-compose up -d --build` followed by `docker-compose exec api alembic upgrade head`. Full walkthrough in [`LAUNCH_GUIDE.md`](https://github.com/Aye-basota/AI-sales-manager/blob/main/LAUNCH_GUIDE.md).
- **Final MVP v3 entry point:** Telegram Admin Bot backed by a team-controlled live instance: [@salesmanager228_bot](https://t.me/salesmanager228_bot).
- **Temporary public web/API access:** the team can expose a running API/site instance publicly using `docker-compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d`, which opens a [localtunnel](https://theboroer.github.io/localtunnel-www/) HTTPS URL. This URL is **ephemeral** and must be recorded separately for each trial if used.
- **Persistent production hosting:** the final public handover level uses a team-operated bot/deployment for course evaluation and documented Docker-based self-hosting for reproduction. Customer-owned deployment is intentionally not claimed without private Week 7 evidence.
- **Recovery:** there is currently no automated backup or restore procedure for the PostgreSQL data or Redis state. Recovery today means re-running `alembic upgrade head` against a fresh database and re-adding Telegram accounts and scripts; there is no documented disaster-recovery runbook yet.
- **Verification after setup:** `GET /health` returns `status`, `db`, and `scheduler` — use it to confirm the API, database, and background scheduler all came up correctly. The latest Sprint 5 local audit ran the maintained CI test command with 991 tests passing and approximately 99% `app/` coverage.

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
- **Anything else:** there is currently no dedicated support channel or issue-response SLA for the customer — problems not covered by the above should go directly to the team. This is a gap the team should close before or during final Week 7 transition if the customer is expected to operate the product independently afterward.

---

## Transition Status

Using the terminology defined for Assignment 6 Part 8:

- **Reached handover level:** `Ready for independent use`.
- **Customer-confirmation status:** `Not yet accepted` until Week 7 written confirmation evidence is collected privately.
- **Final product access artifact:** [@salesmanager228_bot](https://t.me/salesmanager228_bot), backed by the team-operated deployment.
- **Repository and documentation access:** public GitHub repository plus hosted documentation site.
- **Customer-side operation:** not claimed in the public evidence. The customer can reproduce the system using the Docker setup, but customer-owned infrastructure/account transfer has not been publicly evidenced.

This means the product is ready for evaluation and guided independent use, while the remaining transition blocker is evidence/approval rather than a hidden code deployment claim.

---

## Is the Current Documentation Sufficient?

**Sufficient for the reached handover level (`Ready for independent use`).** The documentation set (`README.md`, `LAUNCH_GUIDE.md`, this page) is sufficient for a technically comfortable person to access the team-operated bot and reproduce the product locally end-to-end, but it still assumes team support is available for:

- Provisioning a persistent hosting environment (none exists yet).
- Generating and rotating the Telegram session string (`scripts/generate_session.py` requires an interactive SMS code step).
- Diagnosing failures without a documented recovery runbook.

These limitations are acceptable for the currently claimed handover level, but they should be resolved or explicitly accepted before claiming customer-side deployment or operation.
