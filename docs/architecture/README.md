# Architecture Documentation

This document is the maintained architecture overview for **AI Sales Manager** — an autonomous Telegram outbound sales system with LLM-generated dialogues, campaign scheduling, and lead funnel management.

## Architectural Views

| View | Location | Purpose |
|---|---|---|
| Static view | [`static-view/`](static-view/) | Components, external systems, and communication paths |
| Dynamic view | [`dynamic-view/`](dynamic-view/) | Runtime flows (sequence diagrams) for important workflows |
| Deployment view | [`deployment-view/`](deployment-view/) | Runtime deployment, datastores, and customer access path |

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
