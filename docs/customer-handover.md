# Customer Handover

This page describes the **current actual** handover state of AI Sales Manager. It is updated during Week 6 and Week 7 of Assignment 6 as the transition progresses — it does not describe an aspirational future state.

**Status as of this update:** the Sprint 4 (Week 6) Sprint Review and trial walkthrough was held with the customer (Mark) on 2026-07-12. The team demonstrated a production VPS deployment, and Mark used the product live during the session — but the same session also surfaced a comment, in the raw transcript, that the bot "doesn't work stably when \[the\] laptop is turned on," which conflicts with the intended always-on VPS setup and with the UAT-1 "24/7 availability" pass result. Who this refers to and whether it reflects an actual gap in the VPS deployment is not yet resolved and must be clarified or fixed before Week 7 — see `reports/week6/sprint-review-summary.md`. The product has **not yet** been formally transitioned to the customer (no ownership transfer, no written acceptance). See [Transition Status](#transition-status) below for what that means concretely.

---

## What This Page Covers

- What was transferred, delegated, or retained by the team
- What the customer needs to know about configuration and external services (without exposing secrets)
- How to set up, deploy, recover, and verify the product
- Where to go for normal use, operation, and troubleshooting
- What is still missing before the customer can run the product independently

For step-by-step setup instructions, use [`LAUNCH_GUIDE.md`](../LAUNCH_GUIDE.md) alongside this page — this document explains *what* the handover looks like, `LAUNCH_GUIDE.md` explains *how* to execute it.

---

## Repository, Service, and Account Ownership

| Item | Current arrangement |
|---|---|
| **Source code repository** | Public on GitHub at [`Aye-basota/AI-sales-manager`](https://github.com/Aye-basota/AI-sales-manager), owned by the team. **Not yet transferred** to a customer-owned account or organization. The customer can read, clone, and fork it like any public visitor, but does not currently have write or admin access. |
| **Hosted documentation site** | GitHub Pages at [aye-basota.github.io/AI-sales-manager](https://aye-basota.github.io/AI-sales-manager/), built from this repository. Public and readable by anyone; no separate account or transfer is needed to use it. |
| **Running product instance** | As of Sprint 4 (Week 6), the team has a production VPS deployment, in addition to the on-demand local Docker Compose path (see [Deployment and Access](#deployment-and-access)). The VPS is team-owned infrastructure — nothing has been deployed to infrastructure owned by the customer yet. Whether the VPS deployment is actually independent of any team member's machine is currently **unconfirmed**: the Week 6 session surfaced a comment that the bot is unstable when a laptop is off, which contradicts the intended always-on setup (see the Week 6 Sprint Review summary). Its address is not published in this public document for account-safety reasons (see [`AGENTS.md`](../AGENTS.md#safety-constraints)); it is shared directly with the customer and made available to instructors through the private submission channel. |
| **Telegram seller account** | The live Telegram account used to send messages belongs to whoever supplies the phone number during setup (currently a team-controlled test number). A production handover requires the customer to either supply their own seller phone number or explicitly authorize continued use of the team's number. |
| **LLM provider account (OpenRouter / DashScope)** | Team-controlled test API keys are used during development. No customer-owned LLM API key has been provisioned yet. |
| **Admin Telegram Bot** | Registered via BotFather under a team-controlled bot token. Not yet re-registered under a customer-controlled bot account. |

**Summary:** at this point in Sprint 4, the team retains operational control of the repository, the (now persistent) VPS deployment, and all external service accounts. Nothing has been delegated to the customer yet. This is expected to change during the Week 7 final transition — this page will be updated when it does.

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

- **Local / demo deployment:** `docker-compose up -d --build` followed by `docker-compose exec api alembic upgrade head`. Full walkthrough in [`LAUNCH_GUIDE.md`](../LAUNCH_GUIDE.md).
- **Temporary public access:** the team can expose a running local instance publicly using `docker-compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d`, which opens a [localtunnel](https://theboroer.github.io/localtunnel-www/) HTTPS URL. This URL is **ephemeral** — it only works while the team's host machine and tunnel process are running, and it changes on restart. It is not a substitute for a persistent production deployment.
- **Persistent production hosting:** a production VPS was introduced during Sprint 4 (Week 6), intended to keep the product running without any team member's machine active. Whether it actually achieves that is **unconfirmed as of this update** — the Week 6 session surfaced a comment implying an instability tied to a laptop being on, which the team has not yet resolved or explained (see `reports/week6/sprint-review-summary.md`). There is still no CI/CD deployment pipeline; releases are deployed to the VPS manually. Access is shared directly with the customer and with instructors through the private submission channel rather than published in this document, since the account sends real Telegram messages (see [`AGENTS.md`](../AGENTS.md#safety-constraints)). The VPS remains team-owned and team-operated — deployment on infrastructure owned or operated by the customer is the outstanding item for a "deployed on customer side" handover level.
- **Recovery:** there is currently no automated backup or restore procedure for the PostgreSQL data or Redis state. Recovery today means re-running `alembic upgrade head` against a fresh database and re-adding Telegram accounts and scripts; there is no documented disaster-recovery runbook yet.
- **Verification after setup:** `GET /health` returns `status`, `db`, and `scheduler` — use it to confirm the API, database, and background scheduler all came up correctly. `pytest tests/ -v` (459 tests as of the last MVP v2 release) verifies the codebase itself before deploying a new version.

---

## Main Documentation Entry Points

| Need | Document |
|---|---|
| First-time orientation to the product | [`README.md`](../README.md) |
| Step-by-step non-technical setup | [`LAUNCH_GUIDE.md`](../LAUNCH_GUIDE.md) |
| This handover page | `docs/customer-handover.md` (this file) |
| Contributing changes to the code | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Guidance for AI coding agents working in this repo | [`AGENTS.md`](../AGENTS.md) |
| What has been verified with the customer | [`docs/user-acceptance-tests.md`](user-acceptance-tests.md) |
| Known issues and limitations | [`README.md#известные-ограничения`](../README.md) and `CHANGELOG.md` |
| Architecture and how the system is built | [`docs/architecture/README.md`](architecture/README.md) |
| Full documentation, browsable | [Hosted documentation site](https://aye-basota.github.io/AI-sales-manager/) |

---

## Troubleshooting and Support

- **Setup problems (Docker not starting, session-string generation stuck, etc.):** `LAUNCH_GUIDE.md` includes an "Если не сработало" (*"If it didn't work"*) callout after the Docker install step and after the session-string generation step — check those first.
- **Runtime health check:** `GET /health` reports `status`, `db`, and `scheduler` separately, so a failing check tells you which component is down.
- **Known, already-diagnosed issues:** see [`README.md#известные-ограничения`](../README.md) for the current list of known limitations (inbound flood handling, a low-probability double-reply race condition) with their real-world risk assessment and fix status.
- **Anything else:** there is currently no dedicated support channel or issue-response SLA for the customer — problems not covered by the above should go directly to the team. This is a gap the team should close before or during final Week 7 transition if the customer is expected to operate the product independently afterward.

---

## Transition Status

Following the Week 6 (Sprint 4) transition-readiness meeting and Sprint Review held with the customer (Mark) on 2026-07-12, and using the terminology defined for Assignment 6 Part 8, the team has **not yet reached any of the three target handover levels**:

- **Handover level: none reached yet.** The team demonstrated the product live and shared access with Mark, who used it directly during the session — business/campaign setup, a live AI conversation, and the new lead-discovery feature. However, the session also surfaced an unresolved contradiction about whether the deployment is actually independent of a team member's machine (see the ownership table above and `reports/week6/sprint-review-summary.md`), so the team is not yet claiming `Ready for independent use` until that is clarified or fixed. Mark has **not yet** independently operated the product without the team present, and it is **not yet** deployed or run on infrastructure owned by the customer; all of this is now explicit Week 7 scope.
- **Customer-confirmation status: not yet `Accepted`.** Mark gave positive verbal feedback during the same session — satisfied overall, with two priorities raised (lead-search/parsing quality and response/prompt consistency), both converted into tracked follow-up items for Sprint 5. This feedback was off-record; written confirmation has not yet been collected and is planned before the Week 7 submission, per the Part 8 evidence requirements.

This is the Week 6 status only, not the final Week 7 classification. This section will be updated again after the Week 7 final transition confirmation, per `reports/week6/README.md` and `reports/week7/README.md`.

---

## Is the Current Documentation Sufficient?

**Not yet for independent operation.** The documentation set (`README.md`, `LAUNCH_GUIDE.md`, this page) is sufficient for a technically comfortable person to run the product locally end-to-end, and the Week 6 session showed the customer can use the deployed product directly. It still assumes team support is available for:

- Deploying to or operating the VPS itself (currently team-provisioned and team-operated; no customer-facing deployment runbook exists yet).
- Generating and rotating the Telegram session string (`scripts/generate_session.py` requires an interactive SMS code step).
- Diagnosing failures without a documented recovery runbook.

Explicit customer feedback on this documentation set (as opposed to the product itself) was not part of the 2026-07-12 session and still needs to be collected. These gaps are the concrete follow-up items expected to be resolved between the Week 6 trial and the Week 7 final transition.
