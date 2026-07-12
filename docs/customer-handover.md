# Customer Handover

This page describes the **current actual** handover state of AI Sales Manager. It is updated during Week 6 and Week 7 of Assignment 6 as the transition progresses — it does not describe an aspirational future state.

**Status as of this update:** Sprint 4 (Week 6) trial-readiness review was conducted on 2026-07-12. The product has **not** yet been finally transitioned to the customer; Week 6 produced a trial / handover-candidate state and follow-up items for Week 7.

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
| **Running product instance** | Week 6 trial access was demonstrated through the Telegram Admin Bot / live bot instance: [@salesmanager228_bot](https://t.me/salesmanager228_bot). Nothing has been verified as deployed to infrastructure owned by the customer. |
| **Telegram seller account** | The live Telegram account used to send messages belongs to whoever supplies the phone number during setup (currently a team-controlled test number). A production handover requires the customer to either supply their own seller phone number or explicitly authorize continued use of the team's number. |
| **LLM provider account (OpenRouter / DashScope)** | Team-controlled test API keys are used during development. No customer-owned LLM API key has been provisioned yet. |
| **Admin Telegram Bot** | Registered via BotFather under a team-controlled bot token. This is the main Week 6 product entry point for customer interaction. It has not yet been re-registered under a customer-controlled bot account. |

**Summary:** as of the Week 6 trial-readiness review, the team still retains operational control of the repository, deployment, and external service accounts. The customer saw a live trial and asked to test the bot independently, but customer-side deployment or operation has not been publicly evidenced yet.

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
- **Week 6 trial entry point:** Telegram Admin Bot backed by a team-controlled live instance: [@salesmanager228_bot](https://t.me/salesmanager228_bot).
- **Temporary public web/API access:** the team can expose a running API/site instance publicly using `docker-compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d`, which opens a [localtunnel](https://theboroer.github.io/localtunnel-www/) HTTPS URL. This URL is **ephemeral** and must be recorded separately for each trial if used.
- **Persistent production hosting:** earlier Week 5 UAT evidence says the product was served independently of a developer's local machine. Week 6 does not add evidence that the product is deployed or operated on customer-owned infrastructure, so the final Week 7 handover must clarify whether the final access path is a VPS, a team-controlled bot instance, localtunnel, or a customer-controlled deployment.
- **Recovery:** there is currently no automated backup or restore procedure for the PostgreSQL data or Redis state. Recovery today means re-running `alembic upgrade head` against a fresh database and re-adding Telegram accounts and scripts; there is no documented disaster-recovery runbook yet.
- **Verification after setup:** `GET /health` returns `status`, `db`, and `scheduler` — use it to confirm the API, database, and background scheduler all came up correctly. The latest local Week 6 audit ran `pytest tests/ -v --cov=app --cov-report=term-missing` with 974 tests passing.

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

Using the terminology defined for Assignment 6 Part 8, the team has **not yet reached a final handover-level classification**. Week 6 produced trial-readiness evidence only. As of this update:

- The product is **not yet** independently deployed or operated on the customer's own infrastructure or accounts.
- The customer has asked to test independently, but public evidence of independent customer use has not yet been recorded.
- Written customer confirmation of handover sufficiency has not yet been recorded in the repository; it belongs in the private Week 7 evidence when collected.

This section will be updated with the actual reached level (`Ready for independent use`, `Independently used by customer`, or `Deployed or operated on customer side`) and the customer-confirmation status (`Accepted`, `Accepted with follow-up items`, or `Not yet accepted`) once Week 7 confirmation evidence exists.

---

## Is the Current Documentation Sufficient?

**Partially sufficient for Week 6 trial use; not yet sufficient for final independent operation.** The documentation set (`README.md`, `LAUNCH_GUIDE.md`, this page) is sufficient for a technically comfortable person to run the product locally end-to-end, but it assumes team support is available for:

- Provisioning a persistent hosting environment (none exists yet).
- Generating and rotating the Telegram session string (`scripts/generate_session.py` requires an interactive SMS code step).
- Diagnosing failures without a documented recovery runbook.

These gaps are the concrete follow-up items expected to be resolved or explicitly accepted between the Week 6 trial and the Week 7 final transition.
