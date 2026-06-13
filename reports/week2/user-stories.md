# User Stories and Requirements

## US-01: Getting product information
**Requirement status:** Active
**MoSCoW priority:** Must Have

As a user, I want to know all about the products, so that I can determine what I want.

### Notes and constraints
* The bot must have access to an up-to-date database of the customer's goods/services.
* Requires high accuracy of LLM responses without uncertainty about product properties.

---

## US-02: Contact Product Owner
**Requirement status:** Active
**MoSCoW priority:** Must Have

As a user, I want to contact with product owner, so that we can discuss the details.

### Notes and constraints
* There should be an automatic transfer of contacts or a direct link to the dialog.

---

## US-03: Bot Setup and Funnel Upload
**Requirement status:** Active
**MoSCoW priority:** Must Have

As a sales director, I want to upload scripts and funnels to set up my bot, so that it can start selling my product.

### Notes and constraints
* The interface must support uploading text instructions or JSON/CSV files describing the funnel stages.

---

## US-04: Labor Cost Reduction
**Requirement status:** Active
**MoSCoW priority:** Must Have

As a CEO, I use ASM to reduce the cost of labor.

### Notes and constraints
* The success metric is the percentage of dialogues that are fully processed by AI without involving humans.

---

## US-05: Human Manager Escalation
**Requirement status:** Active
**MoSCoW priority:** Should Have

As a user, I want to talk with a real manager not with the bot, so that I feel more trustful.

### Notes and constraints
* Requires a smooth transfer of the dialog context from the bot to the human.
---

## US-06: Increase Lead Turnover
**Requirement status:** Active
**MoSCoW priority:** Should Have

As a Sales-manager, I use ASM to increase lead turnover.

### Notes and constraints
* The system must process incoming messages in parallel and without delay, increasing the throughput of the funnel.
---

## US-07: 24/7 Availability
**Requirement status:** Active
**MoSCoW priority:** Should Have

As a lead, I text ASM to contact my sales manager at any time.

### Notes and constraints
* The backend of the system must work continuously (24/7) and process messages instantly, even after business hours.
---

## US-08: LLM Provider Selection
**Requirement status:** Active
**MoSCoW priority:** Should Have

As a sales director, I want to select an LLM provider (Qwen, Gemini, DeepSeek) for each ASM from a dropdown, so that I can optimize the balance between dialogue quality and API cost.

### Notes and constraints
 Flexible integration with the API of several providers is required through an abstract class/interface in the code.
---

## US-09: Manual Dialog Takeover
**Requirement status:** Active
**MoSCoW priority:** Could Have

As an operator, I want to take over a dialog from the ASM and continue the conversation manually, so that I can handle complex negotiations with hot leads.

### Notes and constraints
* The interception mechanism should pause the AI agent ('is_paused_by_operator = true`) to prevent simultaneous sending of messages by a bot and a human.
---

## US-010: Telegram Admin Bot for Management
**Requirement status:** Active
**MoSCoW priority:** Could Have

As a sales director, I use ASM to manage task creation and view analytics through a Telegram bot without opening a web interface, so that I can control the process from my messenger.

### Notes and constraints
* Requires the development of a separate interface (Admin Telegram Bot) with authorization by roles.
---

## Initial proposed MVP v1 scope
* **US-01** (Getting product information)
* **US-02** (Contact Product Owner)
* **US-03** (Bot Setup and Funnel Upload)
* **US-04** (Labor Cost Reduction)
