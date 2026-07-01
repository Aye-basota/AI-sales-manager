# Architecture Documentation

This document is the maintained architecture overview for **AI Sales Manager** — an autonomous Telegram outbound sales system with LLM-generated dialogues, campaign scheduling, and lead funnel management.

## Architectural Views

| View | Diagram source | Purpose |
|---|---|---|
| Static view | [`static-view/component-diagram.puml`](static-view/component-diagram.puml) | Components, external systems, and communication paths |
| Dynamic view | [`dynamic-view/inbound-reply-sequence.puml`](dynamic-view/inbound-reply-sequence.puml) | Runtime flows (sequence diagrams) for important workflows |
| Deployment view | [`deployment-view/deployment-diagram.puml`](deployment-view/deployment-diagram.puml) | Runtime deployment, datastores, and customer access path |

## Component Diagram (Static View)

**Diagram source:** [`static-view/component-diagram.puml`](static-view/component-diagram.puml)

### What the diagram shows

The component diagram groups the product into four layers:

1. **External actors and platforms** — Sales Director/Operator, Telegram leads, Telegram MTProto network, and LLM provider APIs (OpenRouter / DashScope).
2. **Application components** — Admin Bot, REST API, scheduler, inbound listener, SellerClient (Pyrogram), LLM engine, guardrails, state machine, humanizer, intent classifier, funnel manager, and supporting services.
3. **Data stores** — PostgreSQL (primary persistence and APScheduler job store) and Redis (conversation cache invalidation).
4. **Communication paths** — outbound campaign processing (scheduler path), inbound reply handling (listener path), and operator management (Admin Bot and REST API both use shared services directly).

Important protocols: **MTProto** (Pyrogram user sessions), **HTTPS** (LLM APIs), **async SQLAlchemy** (PostgreSQL), **in-process calls** between core modules.

### Coupling and cohesion

**Cohesion** is high within bounded packages: `app/llm/` (generation, guardrails, prompts), `app/core/` (scheduler, state machine, humanizer), `app/bots/` (Telegram integration), `app/services/` (persistence, notifications).

**Coupling** is lowest at the **guardrails boundary** ([ADR-001](adr/ADR-001.md), [ADR-004](adr/ADR-004.md)): every outbound and inbound message passes through `apply_guardrails()` before Pyrogram dispatch. The **state machine** ([ADR-002](adr/ADR-002.md)) is a pure module with no I/O, consumed by scheduler and inbound handler alike.

Admin Bot and REST API are **sibling entry points** — both call shared services and the scheduler directly; the bot does not route through the HTTP API.

### Maintainability implications

- New funnel stages require explicit state-machine transitions and tests — predictable but not configurable at runtime.
- LLM provider changes stay isolated in `app/llm/engine.py`.
- Scheduler logic ([ADR-003](adr/ADR-003.md)) centralises anti-spam and working-hours rules.
- **Trade-off:** monolithic `api` container simplifies VPS deployment but couples scheduler restarts with inbound listeners.

### Quality requirements supported or constrained

| QR | Effect of current structure |
|---|---|
| [QR-01](../quality-requirements.md#qr-01) | Guardrails component is the single pre-send gate |
| [QR-02](../quality-requirements.md#qr-02) | Isolated state machine; terminal states enforced centrally |
| [QR-03](../quality-requirements.md#qr-03) | Scheduler owns bounded cycle; LLM latency affects whole pipeline |
| [QR-04](../quality-requirements.md#qr-04) | Anti-repetition inside guardrails on both inbound and outbound paths |

---

## Sequence Diagram (Dynamic View)

**Diagram source:** [`dynamic-view/inbound-reply-sequence.puml`](dynamic-view/inbound-reply-sequence.puml)

### Scenario

A lead replies to an outbound campaign message in Telegram. The system receives the message via Pyrogram, matches the sender to a campaign conversation, classifies intent, updates state and funnel stage, generates an LLM reply with guardrails, applies human-like delays, and sends the response.

### Why this scenario is important

This is the core **MVP v2 conversational path** (improved prompts, natural pacing, structured lead nurturing). It crosses five integration boundaries — Telegram, PostgreSQL, LLM APIs, guardrails, notifications — and failures are immediately visible to leads and operators.

### Architecture decisions, boundaries, and quality requirements

| Step | ADR / QR |
|---|---|
| Intent → state transition | [ADR-002](adr/ADR-002.md), [QR-02](../quality-requirements.md#qr-02) |
| Funnel stage advancement | Multi-stage nurturing (hook → qualification → value → CTA) |
| LLM cascade fallback | Latency and resilience ([QR-03](../quality-requirements.md#qr-03)) |
| `apply_guardrails()` with retry | [ADR-001](adr/ADR-001.md), [QR-01](../quality-requirements.md#qr-01) |
| Anti-repetition (last 5 messages) | [ADR-004](adr/ADR-004.md), [QR-04](../quality-requirements.md#qr-04) |
| Humanizer delays | Natural dialogue pacing (MVP v2 product goal) |
| Hot-lead notification | Operator handover boundary |

### What the diagram shows

The sequence follows one inbound message from Telegram delivery through persistence, intent-driven state update, LLM generation with guardrail retry, humanized send, and optional operator notification — involving Inbound Listener, Conversation Service, State Machine, LLM Engine, Guardrails, Humanizer, SellerClient, and Notification Service.

---

## Deployment Diagram (Deployment View)

**Diagram source:** [`deployment-view/deployment-diagram.puml`](deployment-view/deployment-diagram.puml)

### What the diagram shows

Docker Compose stack on a **production VPS** (Sprint 3 target) or local host:

| Node | Role |
|---|---|
| `api` container | FastAPI :8000, Admin Bot, APScheduler, Pyrogram sessions, static promo site |
| `postgres` container | PostgreSQL 15 — app data + APScheduler job store |
| `redis` container | Redis 7 — cache |
| External | Telegram (MTProto + Bot API), LLM APIs (HTTPS), GitHub Pages (docs only) |

**Customer-facing access:** Telegram Admin Bot, MTProto lead sessions, HTTP :8000 (health/REST/landing page).

### Why this deployment model was chosen

**Single-VPS Docker Compose** matches MVP v2 goals (24/7 availability) without Kubernetes overhead. All runtime components share PostgreSQL state and start together ([ADR-003](adr/ADR-003.md)). The same `docker-compose.yml` used locally deploys to production with environment-specific secrets.

### How deployment supports or constrains the product

**Supports:** `restart: unless-stopped`, dependency health checks, env-based secrets, co-located scheduler job store.

**Constrains:** single-process monolith — deploy restarts all subsystems; no horizontal scaling without shared session management; LLM/Telegram latency depends on external networks.

### Operational considerations for the customer

1. Provide secrets via `.env` (Telegram API, LLM keys, bot token, encryption key).
2. Run `alembic upgrade head` on first deploy and after schema changes.
3. Monitor `/health` (degraded when scheduler is down).
4. Back up PostgreSQL volume (`postgres_data`).
5. Hosted MkDocs docs deploy separately via CI — not part of the runtime VPS stack.

---

## Architecture Decision Records

Important design choices are captured as ADRs in [`adr/`](adr/). Each ADR documents context, the adopted decision, consequences, and linked quality requirements.

| ADR | Title | Status | Quality requirements |
|---|---|---|---|
| [ADR-001](adr/ADR-001.md) | LLM Output Guardrails | Accepted | [QR-01](../quality-requirements.md#qr-01) |
| [ADR-002](adr/ADR-002.md) | Deterministic Conversation State Machine | Accepted | [QR-02](../quality-requirements.md#qr-02) |
| [ADR-003](adr/ADR-003.md) | Scheduler-Driven Outbound Processing | Accepted | [QR-03](../quality-requirements.md#qr-03) |
| [ADR-004](adr/ADR-004.md) | Anti-Repetition Check for Generated Messages | Accepted | [QR-04](../quality-requirements.md#qr-04) |

## How the Architecture and Decisions Fit Together

AI Sales Manager follows a **layered, in-process architecture** deployed as Docker containers (FastAPI app, Admin Bot, PostgreSQL, Redis). The three views and four ADRs describe the same system from different angles:

```
┌─────────────────────────────────────────────────────────────────┐
│  Customer / Operator (Telegram, Admin Bot, future Web UI)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Application layer (FastAPI + aiogram Admin Bot)                │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │ Scheduler    │  │ Inbound     │  │ Campaign / Script API  │  │
│  │ (ADR-003)    │  │ Handler     │  │                        │  │
│  └──────┬───────┘  └──────┬──────┘  └────────────────────────┘  │
│         │                 │                                     │
│  ┌──────▼─────────────────▼──────┐  ┌────────────────────────┐  │
│  │ State Machine (ADR-002)       │  │ LLM Engine             │  │
│  └───────────────────────────────┘  └───────────┬────────────┘  │
│                                                 │               │
│                          ┌──────────────────────▼────────────┐  │
│                          │ Guardrails (ADR-001, ADR-004)       │  │
│                          └──────────────────────┬────────────┘  │
│                                                 │               │
│                          ┌──────────────────────▼────────────┐  │
│                          │ SellerClient (Pyrogram MTProto)   │  │
│                          └─────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  PostgreSQL (data + APScheduler job store)  │  Redis  │  LLM APIs │
└─────────────────────────────────────────────────────────────────┘
```

### Static view → structure

The static view shows **what the system is made of**: internal modules (`scheduler`, `state_machine`, `guardrails`, `llm/engine`, `SellerClient`) and externals (Telegram, OpenRouter/DashScope, PostgreSQL, Redis). Low coupling between guardrails, state machine, and scheduler keeps each concern testable in isolation — which directly supports the Testability and Modifiability goals behind [QR-01](../quality-requirements.md#qr-01)–[QR-04](../quality-requirements.md#qr-04).

### Dynamic view → behaviour

The dynamic view traces **how a request flows** — typically the outbound path: scheduler tick → load campaign contacts → select account → LLM generate → guardrails → Pyrogram send → update state. This flow crosses the boundaries defined in ADR-001 (pre-send safety), ADR-003 (when and how sends happen), ADR-002 (state updates after replies), and ADR-004 (repetition rejection inside guardrails).

### Deployment view → operations

The deployment view shows **where code runs**: a single application container hosts FastAPI, APScheduler jobs, and Pyrogram sessions; PostgreSQL holds persistent state and scheduler jobs; Redis supports caching. Customer access is through the Telegram Admin Bot and deployed Docker stack. Operational constraints (timezone, cooldown recovery, daily counter reset) are implemented inside ADR-003's scheduler jobs.

### ADRs → rationale and quality traceability

Each ADR explains **why** a specific pattern was chosen and which measurable quality requirement it satisfies:

- **ADR-001 + ADR-004** form the **pre-dispatch safety gate** for all LLM output — confidentiality and user-error protection before any Telegram send.
- **ADR-002** ensures **funnel integrity** — terminal states stop further messaging and keep analytics trustworthy.
- **ADR-003** provides **timed, recoverable outbound processing** — the 5-minute cycle, persistent job store, and account rotation enforce performance and availability constraints.

Bidirectional traceability is maintained:

- Each ADR links to its quality requirement(s) in [`docs/quality-requirements.md`](../quality-requirements.md).
- Each quality requirement links back to its ADR and automated test in [`docs/quality-requirement-tests.md`](../quality-requirement-tests.md).

When product scope, deployment, or quality targets change, update the relevant view diagram **and** the affected ADR (or add a new ADR that supersedes the old one) rather than silently changing implementation.

## Quality Requirements and Architecture

Full quality requirement definitions: [`docs/quality-requirements.md`](../quality-requirements.md)

Automated verification mapping: [`docs/quality-requirement-tests.md`](../quality-requirement-tests.md)

## Related Documentation

- Development process and git workflow: [`docs/development-process.md`](../development-process.md)
- Testing strategy: [`docs/testing.md`](../testing.md)
- Definition of Done: [`docs/definition-of-done.md`](../definition-of-done.md)
