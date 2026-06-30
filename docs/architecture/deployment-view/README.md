# Deployment View

The deployment view shows where the product runs, how components are packaged, and how customers and operators reach the system.

## Deployment Diagram

**Source (diagrams-as-code):** [`deployment-diagram.puml`](deployment-diagram.puml)

Render locally with PlantUML:

```bash
plantuml docs/architecture/deployment-view/deployment-diagram.puml
```

### What the diagram shows

The diagram depicts the **Docker Compose stack** that runs on a production VPS (Sprint 3 target) or a local development host:

| Node | Role |
|---|---|
| **api container** | FastAPI on port 8000, Admin Bot, APScheduler, Pyrogram user sessions, static promo site |
| **postgres container** | PostgreSQL 15 — application data and APScheduler SQLAlchemy job store |
| **redis container** | Redis 7 — cache and auxiliary session helpers |
| **Telegram servers** | External MTProto and Bot API endpoints for lead messaging and Admin Bot |
| **LLM API endpoints** | External HTTPS APIs (OpenRouter / DashScope) for message generation |
| **GitHub Pages** | Hosted MkDocs documentation (deployed separately via CI, not runtime) |

**Customer-facing access paths:**

1. **Telegram Admin Bot** — primary operator interface for campaign management (MVP v2).
2. **Telegram MTProto sessions** — leads interact with live user accounts; no separate lead-facing web app in MVP v2.
3. **HTTP port 8000** — health checks, REST API, and promo landing page (`site/`).
4. **Hosted documentation** — public architecture, quality, and run instructions at GitHub Pages.

## Why this deployment model was chosen

**Single-VPS Docker Compose** was selected for MVP v2 because:

- The Sprint Goal requires **24/7 availability** on a production VPS without introducing Kubernetes or multi-service orchestration overhead for a small team.
- All runtime components (API, bots, scheduler, Pyrogram clients) share PostgreSQL state and must start together — a monolithic container matches the current architecture ([static view](../static-view/README.md)).
- Docker Compose is already used for local development (`docker-compose.yml`), so production deployment reuses the same artefact with environment-specific secrets.
- APScheduler's SQLAlchemy job store ([ADR-003](../adr/ADR-003.md)) requires PostgreSQL co-location; splitting scheduler into a separate host would add network latency and deployment complexity without immediate benefit at current scale.

Alternatives deferred: managed PaaS (Render, Fly.io), Kubernetes, and separate worker containers for LLM-heavy tasks.

## How deployment supports or constrains the product

**Supports:**

- `restart: unless-stopped` on all services gives basic fault recovery aligned with MVP v2 availability goals.
- Health checks on PostgreSQL and Redis prevent the API container from starting before dependencies are ready.
- Environment variables isolate secrets and per-environment configuration (LLM keys, Telegram credentials).
- Volume mounts in development allow hot reload; production builds use immutable images.

**Constrains:**

- All Pyrogram sessions and scheduler jobs live in one process — a crash or deploy restarts inbound listeners and pending scheduler ticks together.
- LLM API latency and Telegram FloodWait errors depend on external networks outside the VPS boundary.
- Horizontal scaling (multiple API replicas) would require shared session management and scheduler leader election not implemented in MVP v2.

## Operational considerations

When deploying or operating for the customer:

1. **Secrets** — provide `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `ADMIN_BOT_TOKEN`, LLM API keys, and `SESSION_ENCRYPTION_KEY` via `.env`; never commit to the repository.
2. **Database migrations** — run `alembic upgrade head` after container start on first deploy and after schema changes.
3. **Timezone** — scheduler cron jobs (daily counter reset) use Europe/Moscow; script working hours use per-script timezones.
4. **Monitoring** — use `/health` endpoint; degraded status when scheduler is not running ([QR-03](../quality-requirements.md#qr-03) proxy).
5. **Backups** — back up PostgreSQL volume (`postgres_data`); session strings and conversation history are not recoverable from Telegram alone.
6. **Documentation site** — updates to `docs/` deploy automatically to GitHub Pages on push to `main`; this is independent of the product VPS.

For temporary public demos without a VPS, the team may use `docker-compose.tunnel.yml` with localtunnel; MVP v2 targets persistent VPS hosting for reliable customer access.
