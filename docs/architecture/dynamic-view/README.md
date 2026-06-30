# Dynamic View

The dynamic view documents important runtime flows as sequence diagrams so the team can reason about cross-component interactions, integration boundaries, and quality-relevant behaviour.

## Sequence Diagram — Inbound Lead Reply

**Source (diagrams-as-code):** [`inbound-reply-sequence.puml`](inbound-reply-sequence.puml)

Render locally with PlantUML:

```bash
plantuml docs/architecture/dynamic-view/inbound-reply-sequence.puml
```

### Scenario

A lead replies to an outbound campaign message in Telegram. The system must:

1. Receive the message through a live Pyrogram session (`SellerClient`).
2. Match the sender to a contact and running campaign conversation.
3. Persist the inbound message and classify intent.
4. Update conversation state and funnel stage.
5. Generate a context-aware LLM reply with guardrails and human-like delays.
6. Send the reply and notify the operator on hot-lead signals.

This is the core **MVP v2 conversational flow**: improved prompts, natural multi-stage dialogue, and structured lead nurturing before guiding the user toward a meeting booking.

### Why this scenario matters

Inbound reply handling is the highest-risk user-facing path for MVP v2:

- It combines **five integration boundaries** (Telegram, PostgreSQL, LLM APIs, guardrails, notifications) in one request.
- It directly implements the Sprint Goal of a **more natural conversational flow** and **trust-building lead nurturing** — the AI must respond in context, advance the funnel stage, and avoid repetitive or unsafe text.
- Failures here are immediately visible to leads and operators (wrong state, robotic text, spam-like repetition, or unsafe content).

Outbound campaign processing ([ADR-003](../adr/ADR-003.md)) follows a similar LLM → guardrails → send pattern but is timer-driven rather than event-driven. The inbound path is documented here because it best illustrates MVP v2 AI behaviour.

### Architecture decisions and quality requirements illustrated

| Step in diagram | Related decision / requirement |
|---|---|
| Intent classification → state transition | [ADR-002](../adr/ADR-002.md) — deterministic funnel integrity ([QR-02](../quality-requirements.md#qr-02)) |
| Funnel stage advancement | Multi-stage nurturing (hook → qualification → value → CTA) |
| LLM generate with cascade fallback | Provider resilience; latency affects reply time ([QR-03](../quality-requirements.md#qr-03)) |
| `apply_guardrails()` with retry | [ADR-001](../adr/ADR-001.md) — content safety ([QR-01](../quality-requirements.md#qr-01)) |
| Anti-repetition against last 5 messages | [ADR-004](../adr/ADR-004.md) — user error protection ([QR-04](../quality-requirements.md#qr-04)) |
| Humanizer read/typing delays | Natural conversational pacing (MVP v2 product goal) |
| Hot-lead notification | Operator handover when meeting intent detected |

### What the diagram shows

The sequence follows one inbound message from Telegram delivery through persistence, intent-driven state update, LLM generation with guardrail retry, humanized send, and optional operator notification. Multiple components interact (Inbound Listener, Conversation Service, State Machine, LLM Engine, Guardrails, Humanizer, SellerClient, Notification Service), making this a non-trivial cross-cutting workflow suitable for architecture review and test design.
