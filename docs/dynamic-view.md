# Dynamic View — AI Sales Manager

## Chosen Scenario: AI-Driven Telegram Reply Processing

**Why this scenario?**
This is the core value-delivering flow of the system. When a lead replies on Telegram, the system must: retrieve conversation history, call an LLM to generate a contextual reply or detect qualification, persist results, and conditionally notify the Sales Director. It spans five distinct components with multiple synchronous and asynchronous transactions — making it the most architecturally revealing scenario.

---

## UML Sequence Diagram

```mermaid
sequenceDiagram
    autonumber

    participant TG as :TelegramPlatform
    participant TC as :TelegramClient
    participant DM as :DialogManager
    participant DB as :ConversationRepository
    participant LLM as :LLMService
    participant LS as :LeadStatusService
    participant NS as :NotificationService

    TG ->> TC: incomingMessage(contactId, text)
    TC ->> DM: handleMessage(contactId, text)

    DM ->> DB: getHistory(contactId)
    DB -->> DM: conversationHistory[]

    DM ->> LLM: generateReply(aiManagerConfig, history, text)
    LLM -->> DM: {reply: string, signal: QUALIFIED | CONTINUE | REJECT}

    DM ->> DB: saveMessage(contactId, role=user, text)
    DM ->> DB: saveMessage(contactId, role=assistant, reply)

    alt signal == QUALIFIED
        DM ->> LS: updateLeadStatus(contactId, QUALIFIED)
        LS ->> DB: updateContact(contactId, status=QUALIFIED)
        DB -->> LS: OK
        LS -->> DM: OK
        DM ->> NS: notifySalesDirector(contactId, conversationSummary)
        NS ->> TG: sendMessage(salesDirectorTelegramId, alert)
    else signal == REJECT
        DM ->> LS: updateLeadStatus(contactId, REJECTED)
        LS ->> DB: updateContact(contactId, status=REJECTED)
        DB -->> LS: OK
        LS -->> DM: OK
    else signal == CONTINUE
        DM ->> TC: sendMessage(contactId, reply)
        TC ->> TG: outgoingMessage(contactId, reply)
    end

    TC -->> DM: done
    DM -->> TC: ack
```

---

## Component Roles

| Component | Responsibility |
|-----------|---------------|
| `:TelegramPlatform` | External Telegram API/MTProto network — delivers and receives messages |
| `:TelegramClient` | Pyrofork/Telethon wrapper — listens for incoming events, sends outgoing messages |
| `:DialogManager` | Core orchestrator — routes messages, manages the conversation loop |
| `:ConversationRepository` | Persistence layer — stores message history and contact status |
| `:LLMService` | LLM abstraction (Qwen / Gemini / DeepSeek) — generates contextual replies and qualification signals |
| `:LeadStatusService` | Manages lead funnel state transitions (cold → warm → hot → qualified/rejected) |
| `:NotificationService` | Sends Telegram bot alerts to the Sales Director on key events |

---

## Quality Characteristic Reasoning

**Primary: Performance Efficiency (Response Latency)**

The sequence diagram makes latency bottlenecks visible:
- Steps 5–6 (LLM call) are the dominant latency source — network round-trip to external LLM API.
- Steps 3–4 (DB read) and 7–8 (DB writes) add sequential I/O cost.
- The `alt` branch (steps 9–17) adds conditional work on top of the base path.

By reading the diagram, the team can reason: "Can we parallelize DB history fetch and LLM warm-up?" and "Should we make the notification (step 16) async to unblock the response path?"

**Secondary: Reliability (Fault Tolerance)**

The diagram exposes single points of failure:
- If `:LLMService` times out (step 6), the dialogue stalls — a retry or fallback LLM must be designed.
- If `:TelegramClient` fails to deliver the reply (step 17), the lead is silently uncontacted — a dead-letter queue or retry mechanism is needed.

These failure modes are invisible in the Static Component Diagram but become obvious in the sequence view.

---

## Diagram Source

Tool: [Mermaid](https://mermaid.js.org/) — renders natively in GitHub Markdown.
