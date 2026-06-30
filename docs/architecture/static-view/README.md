# Static View

The static view shows the main internal components of AI Sales Manager, external systems they interact with, and the primary communication paths between them.

## Component Diagram

**Source (diagrams-as-code):** [`component-diagram.puml`](component-diagram.puml)

Render locally with PlantUML:

```bash
plantuml docs/architecture/static-view/component-diagram.puml
```

Or paste the source into the [PlantUML online server](https://www.plantuml.com/plantuml/uml).

### What the diagram shows

The component diagram groups the product into four layers:

1. **External actors and platforms** — Sales Director/Operator, Telegram leads, Telegram MTProto network, and LLM provider APIs (OpenRouter / DashScope).
2. **Application components** — Admin Bot, REST API, scheduler, inbound listener, SellerClient (Pyrogram), LLM engine, guardrails, state machine, humanizer, intent classifier, funnel manager, and supporting services.
3. **Data stores** — PostgreSQL (primary persistence and APScheduler job store) and Redis (cache).
4. **Communication paths** — outbound campaign processing (scheduler path), inbound reply handling (listener path), and operator management (Admin Bot / API).

Key relations:

| From | To | Protocol / interface |
|---|---|---|
| Scheduler | LLM Engine → Guardrails → SellerClient | in-process calls; HTTPS to LLM APIs |
| Inbound Listener | Intent Classifier → State Machine → LLM Engine | in-process; event-driven from Pyrogram |
| Admin Bot / API | PostgreSQL | async SQLAlchemy |
| SellerClient | Telegram | MTProto user sessions |

## Coupling, Cohesion, and Maintainability

**Cohesion** is generally high within bounded modules:

- `app/llm/` owns generation, guardrails, prompts, and intent classification.
- `app/core/` owns scheduling, state machine, humanizer, and account selection.
- `app/bots/` owns Telegram integration (Admin Bot, SellerClient, inbound listener).
- `app/services/` owns conversation persistence and notifications.

**Coupling** is lowest around the pre-send guardrails boundary ([ADR-001](../adr/ADR-001.md), [ADR-004](../adr/ADR-004.md)): any outbound or inbound message must pass through `apply_guardrails()` before Pyrogram dispatch. The state machine ([ADR-002](../adr/ADR-002.md)) is a pure module with no I/O, consumed by both scheduler and inbound handler.

**Maintainability implications:**

- New funnel stages or conversation states require updating the state machine table and tests — explicit but predictable.
- LLM provider changes are isolated to `app/llm/engine.py` without touching Telegram code.
- Scheduler logic ([ADR-003](../adr/ADR-003.md)) centralises anti-spam and working-hours rules, avoiding duplication across API and Admin Bot entry points.

Trade-off: the application runs as a **monolithic container** (FastAPI + bots + scheduler + Pyrogram clients). This simplifies MVP v2 deployment on a single VPS but couples process restarts to all subsystems.

## Supported and Constrained Quality Requirements

| Quality requirement | How the structure supports or constrains it |
|---|---|
| [QR-01](../quality-requirements.md#qr-01) Confidentiality | Guardrails component is the single gate before Telegram send |
| [QR-02](../quality-requirements.md#qr-02) Fault tolerance | Isolated state machine module; terminal states enforced centrally |
| [QR-03](../quality-requirements.md#qr-03) Time behaviour | Scheduler component owns bounded processing cycle; LLM latency affects entire pipeline |
| [QR-04](../quality-requirements.md#qr-04) User error protection | Anti-repetition lives inside guardrails; shares inbound and outbound paths |

Modifiability and testability benefit from the separation of guardrails, state machine, and scheduler, but performance scaling is constrained by the monolithic deployment model until the team splits workers or queues.
