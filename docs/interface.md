# AI Sales Manager — Interface Specification

## Interface Type
Web application (responsive, desktop-first) with a complementary Telegram bot.

## Intended Users
- **Sales Director** — primary user; manages AI managers, contacts, tasks, and reviews analytics.
- **Operator** — secondary user; monitors dialogs and manually qualifies leads.

---

## Screens and Flows

### 1. Login / Authentication
- Email/password or Telegram-based auth.
- Role-based redirect: Sales Director → Dashboard, Operator → Dialogs.

### 2. Dashboard (Home)
- Summary stats: total contacts, active tasks, qualified leads, conversion rate.
- Quick-action buttons: "New AI Manager", "New Task", "Import Contacts".
- Recent activity feed.

### 3. Contacts Management (`/contacts`)
#### 3a. Contact List
- Table with columns: Name, Telegram ID / Phone, Position, Company, Status (cold/warm/hot), Date Added.
- Search bar + filter by status, company, date range.
- Bulk select → "Add to Task".

#### 3b. Import Contacts
- Upload CSV/Excel file (drag-and-drop or file picker).
- Preview parsed data before importing.
- Map columns: name, telegram_id, phone, position, company.
- Success/error feedback with count.

#### 3c. Contact Parsing (US-09)
- Form fields: Industry, Position, Geography.
- "Start Parsing" button with progress indicator.
- Results preview before saving to contact base.

### 4. AI Manager Studio (`/ai-managers`)
#### 4a. AI Manager List
- Cards or table showing: Name, Role, Status (active/inactive), Linked Task count.
- "Create New" button (max 5 limit indicator).
- Duplicate button (US-11).

#### 4b. Create / Edit AI Manager
- **Name** field.
- **Role / Persona** textarea: describe the AI's role, tone, and style.
- **Target Audience** textarea: describe the ideal lead profile.
- **Dialogue Goal** textarea: what the AI should achieve (e.g., book a call).
- **Success Criterion** textarea: what constitutes a successful conversation.
- **LLM Provider** dropdown: Qwen, Gemini, DeepSeek (US-13).
- Save / Cancel buttons.

### 5. Task Management (`/tasks`)
#### 5a. Task List
- Table: Task Name, AI Manager, Contact Base, Status (running/paused/stopped), Progress (X/Y processed).
- Start / Pause / Stop buttons per task.

#### 5b. Create Task
- Step 1: Select AI Manager (from existing list).
- Step 2: Select Contact Base (from imported/parsed contacts).
- Step 3: Configure Working Hours (checkbox + time picker, default 09:00–18:00 MSK).
- Step 4: Configure Message Interval (initial message + follow-up after N hours).
- Step 5: Review & Launch.

### 6. Dialog Monitor (`/dialogs`)
- List of all active/inactive dialogs.
- Each row: Contact Name, AI Manager, Last Message, Status (cold/warm/hot/qualified/rejected).
- Click to expand → full message history with timestamps.
- Operator action buttons: "Mark Qualified", "Mark Rejected" (US-07).
- Tags on ambiguous replies (US-12).
- Search by contact name or status filter.

### 7. Funnel & Analytics (`/analytics`)
#### 7a. Funnel Visualization
- 3–4 stage funnel: Cold → Warm → Hot → Qualified.
- Count at each stage with conversion rate.
- Historical trend (line chart) for each stage over time.

#### 7b. Reports
- Contacts Found (total parsed/imported).
- Contacts Contacted (messaged by AI).
- Moved to Next Stage (per stage).
- Qualified / Rejected breakdown.

### 8. Settings (`/settings`)
- Working hours configuration (default 09:00–18:00 MSK).
- Message interval settings.
- LLM API key configuration.
- Notification preferences (Telegram bot alerts).

---

## User Flows

### Flow A: Import Contacts → Create AI Manager → Launch Task
1. Upload CSV at `/contacts/import` → preview → confirm.
2. Create AI manager at `/ai-managers/new` → fill persona details → save.
3. Create task at `/tasks/new` → select AI manager + contact base → configure hours → launch.
4. Monitor progress on Dashboard and `/dialogs`.

### Flow B: Daily Review
1. Check Dashboard for summary stats.
2. Review `/analytics` funnel stages.
3. Open `/dialogs` to manually qualify leads.
4. Export qualified leads or flag for follow-up.

---

## States

### Empty States
- No contacts yet → "Import your first contact base to get started" with CTA.
- No AI managers yet → "Create your first AI manager" with CTA.
- No tasks yet → "Launch your first task" with CTA.
- No dialogs yet → "Dialogs will appear once tasks are running."

### Loading States
- Skeleton placeholders on table and card loads.
- Progress bar during CSV parsing and task execution.

### Error States
- CSV parse error → inline error message with row details.
- Task failure → status badge (red) + error detail tooltip.
- API timeout → retry button with message.

### Success States
- Contact import → toast: "150 contacts imported successfully".
- Task launched → toast + redirect to task detail.
- Lead qualified → inline confirmation + status update.

---

## Telegram Bot (Secondary Interface — US-10)
- Commands:
  - `/start` — register for notifications.
  - `/tasks` — list active tasks.
  - `/stats` — quick funnel summary.
  - `/help` — list available commands.

---

## Implementation Status for MVP v0
| Screen | Implemented | Mocked | Planned |
|--------|------------|--------|---------|
| Login | — | Mock | MVP v1 |
| Dashboard | — | Mock | MVP v1 |
| Contact Import | Partial (CSV API exists) | — | MVP v0 |
| Contact Parsing | — | — | V2 |
| AI Manager Studio | — | — | MVP v1 |
| Task Management | — | — | MVP v1 |
| Dialog Monitor | — | — | MVP v1 |
| Funnel & Analytics | — | — | MVP v1 |
| Settings | — | — | MVP v1 |
| Telegram Bot | Partial (bot exists) | — | MVP v0 |
