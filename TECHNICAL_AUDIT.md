# AI Sales Manager — Техническое описание текущей реализации MVP

> Дата аудита: 2026-06-09
> Версия кода: актуальный HEAD

---

## Блок 1. Архитектура системы

### Общая схема архитектуры

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Sales Manager                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI (app/main.py)                                                      │
│  ├── REST API (app/api/)        →  CRUD для scripts, campaigns, contacts,   │
│  │                                 conversations, analytics                 │
│  ├── Admin Bot (app/bots/admin_bot.py)  →  aiogram 3.x, FSM, команды       │
│  ├── Scheduler (app/core/scheduler.py)  →  APScheduler, раз в 5 мин         │
│  └── Inbound Listener (app/bots/inbound_listener.py) → Pyrogram MTProto    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Core Services (app/core/, app/services/, app/llm/)                         │
│  ├── State Machine (app/core/state_machine.py)                              │
│  ├── Humanizer (app/core/humanizer.py)                                      │
│  ├── Account Manager (app/core/account_manager.py)                          │
│  ├── Contact Import (app/services/contact_import.py)                        │
│  ├── Conversation Service (app/services/conversation_service.py)            │
│  ├── Notification Service (app/services/notification_service.py)            │
│  └── LLM Engine (app/llm/engine.py, prompts.py, guardrails.py)              │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL 15 (asyncpg)            Redis 7 (redis.asyncio)                 │
│  ├── SQLAlchemy 2.0 Async           ├── Кэш контекста диалога               │
│  ├── Alembic миграции               └── Очереди / rate-limit (план)         │
└─────────────────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────────────────┐
│  Внешние API                                                                │
│  ├── Telegram Bot API (aiogram) — Admin Bot                                 │
│  ├── Telegram MTProto (Pyrogram) — User-аккаунты для outbound/inbound       │
│  └── OpenRouter (httpx) — LLM-провайдер (Qwen / Gemini / DeepSeek)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Технологический стек

| Слой | Технология | Версия | Файл/Модуль |
|------|-----------|--------|-------------|
| Backend | FastAPI | 0.111.0 | `app/main.py` |
| Async Server | Uvicorn | 0.30.0 | `Dockerfile`, `docker-compose.yml` |
| ORM | SQLAlchemy (asyncio) | 2.0.30 | `app/db/session.py` |
| БД | PostgreSQL | 15-alpine | `docker-compose.yml` |
| Миграции | Alembic | 1.13.0 | `alembic/versions/` |
| Кэш / Очереди | Redis | 7-alpine | `app/db/redis.py` |
| Admin Bot | aiogram | 3.6.0 | `app/bots/admin_bot.py` |
| User Client | Pyrogram | 2.0.106 | `app/bots/seller_client.py` |
| LLM API | httpx + OpenRouter | 0.27.0 | `app/llm/engine.py` |
| Планировщик | APScheduler | 3.10.4 | `app/core/scheduler.py` |
| Валидация / сериализация | Pydantic + Pydantic-Settings | 2.7.0 / 2.2.0 | `app/schemas/`, `app/config.py` |
| Импорт данных | pandas + openpyxl | 2.2.0 / 3.1.0 | `app/services/contact_import.py` |
| Шифрование сессий | cryptography (Fernet) | 42.0.0 | `app/bots/seller_client.py` |
| Тестирование | pytest + pytest-asyncio + pytest-mock | 8.2.0 | `tests/` |

### Монолит или микросервисы?

**Статус: Реализовано — Монолит**

Выбран **монолитный подход** с модульной структурой внутри одного Python-пакета `app/`.

- **Обоснование:** MVP сжатых сроков (2 месяца), небольшая команда, необходимость быстрой итерации. Разделение на сервисы в `docker-compose.yml` выполнено только по runtime-ролям (`api`, `scheduler`, `admin-bot`), но кодовая база общая.
- **Риски:** scheduler и inbound listener работают как отдельные контейнеры, но используют общую БД и код. Нет явного message broker между компонентами (используется polling БД).

### Схема взаимодействия с внешними API

| API | Библиотека | Назначение | Хранение credentials |
|-----|-----------|------------|---------------------|
| Telegram Bot API | `aiogram` (3.6.0) | Admin-бот для оператора / владельца | `ADMIN_BOT_TOKEN` в `.env` (`app/config.py`) |
| Telegram MTProto (User API) | `Pyrogram` (2.0.106) | Outbound сообщения + inbound listener для живых аккаунтов | `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` + `session_string` (шифруется Fernet, хранится в БД `telegram_accounts.session_string`) |
| LLM (OpenRouter) | `httpx` | Генерация ответов ИИ | `OPENROUTER_API_KEY` в `.env` |

---

## Блок 2. Управление контактами (Lead Base)

### Импорт: CSV / Excel

**Статус: Готово**

- **Модули:** `app/services/contact_import.py`, `app/api/contacts.py` (endpoint `/contacts/import`), `scripts/import_contacts.py` (CLI)
- **Поддерживаемые форматы:** `.csv`, `.xlsx`, `.xls`
- **Обязательные поля:** В текущей реализации **нет жёстко обязательных полей** — pandas читает любые столбцы, соответствующие модели `ContactCreate` (`app/schemas/contact.py`). Ожидаемые колонки:
  - `first_name`, `last_name`, `phone`, `telegram_username`, `company_name`, `position`, `city`, `industry`, `status`
- **Валидация:** Проверка на неизвестные колонки (`_ALLOWED_COLUMNS`). Если файл содержит столбцы вне списка — выбрасывается `ValueError` с перечнем допустимых.
- **Дубликаты:** **НЕ РЕАЛИЗОВАНО**. Нет проверки на дубли по phone, telegram_username или telegram_user_id. Контакты импортируются как есть, дубли создают новые записи в БД.
  - *Почему:* сроки MVP, решено отложить.
  - *Альтернатива:* Вручную очищать базу перед импортом; добавить `UNIQUE` constraint + upsert логику на следующей итерации.

### Парсинг: поиск контактов по критериям

**Статус: НЕ РЕАЛИЗОВАНО**

- Нет интеграции с Rosprofile, открытыми базами, кастомным парсером.
- *Почему:* MVP фокусируется на работе с уже имеющейся базой заказчика (CSV/Excel). Парсинг — отдельный проект с юридическими рисками.
- *Альтернатива:* Импортировать готовые базы через `/contacts/import` или `/importcsv` в Admin Bot.

### Хранение

- **Таблица:** `contacts` (`app/models/contact.py`)
- **Схема:**
  ```sql
  id UUID PRIMARY KEY DEFAULT gen_random_uuid()
  telegram_username VARCHAR(32)
  telegram_user_id BIGINT          -- ключевое поле для отправки через MTProto
  phone VARCHAR(20)
  first_name VARCHAR(100)
  last_name VARCHAR(100)
  company_name VARCHAR(200)
  position VARCHAR(100)
  city VARCHAR(100)
  industry VARCHAR(100)
  source VARCHAR(50) DEFAULT 'csv_import'
  icp_score INTEGER
  status VARCHAR(20) DEFAULT 'new'
  assigned_script_id UUID FK → scripts.id
  assigned_account_id UUID       -- привязка к Telegram-аккаунту
  created_at TIMESTAMPTZ DEFAULT now()
  updated_at TIMESTAMPTZ DEFAULT now()
  ```
- **История изменений статуса:** Нет отдельной таблицы audit-log. Текущий статус хранится только в `contacts.status`. История сообщений по контакту есть в таблице `messages` через `conversations`.

### Формат данных: загрузка через Telegram-бот или веб

- **Реализовано и то, и другое:**
  - **REST API:** `POST /contacts/import` (multipart/form-data, `UploadFile`) — `app/api/contacts.py:64`
  - **Telegram Bot:** команда `/importcsv` в Admin Bot (`app/bots/admin_bot.py:529`) — FSM `CSVImportFSM`, принимает документ `.csv`
  - **CLI:** `python -m scripts.import_contacts <file>`

---

## Блок 3. AI Manager / Скрипты продаж

### Создание скрипта

**Статус: Готово**

- **Интерфейсы:**
  1. **REST API:** `POST /scripts` (`app/api/scripts.py:29`) — JSON body по `ScriptCreate` schema
  2. **Telegram Bot (Admin):** FSM `ScriptCreateFSM` (`app/bots/admin_bot.py:36`) — пошаговое создание через `/newscript`
- **Настраиваемые параметры** (`app/models/script.py`, `app/schemas/script.py`):
  - `name` — название скрипта
  - `role_prompt` — роль ИИ (системный промпт)
  - `target_audience` — ЦА
  - `goal` — цель диалога
  - `success_criteria` — критерий успешного лида
  - `tone` — тон (professional / friendly / casual)
  - `max_messages` — максимум сообщений на контакт (default 2)
  - `follow_up_delay_hours` — задержка follow-up в часах (default 24)
  - `working_hours_start`, `working_hours_end` — рабочие часы
  - `timezone` — таймзона (default Europe/Moscow)
  - `is_active` — активен ли скрипт

### Нелинейный диалог

**Статус: Частично реализовано (гибрид prompt-engineering + state-machine)**

- **State Machine:** `app/core/state_machine.py`
  - Состояния: `cold`, `warm`, `hot`, `meeting_booked`, `closed`, `follow_up`, `objection_handler`
  - События: `initial_message`, `positive_reply`, `negative_reply`, `no_reply_24h`, `no_reply_48h`, `meeting_intent`, `objection`
  - Функция `transition(current_state, event) → new_state`
- **Prompt Engineering:** `app/llm/prompts.py`
  - `build_system_prompt(script)` — формирует детальный системный промпт с правилами: «пиши как живой человек», «не используй markdown», «не говори что ты ИИ», техники работы с возражениями, предложение 2 вариантов времени для звонка.
  - `build_user_prompt(...)` — подаёт контекст диалога, факты о лиде, последнее сообщение агента, ответ клиента.
- **Обработка нестандартных ответов:** Через LLM + few-shot examples в промпте. Нет жёсткого decision-tree — модель сама формирует ответ на основе системного промпта и истории.

### Множественные скрипты

**Статус: Готово**

- Таблица `scripts` позволяет хранить неограниченное количество скриптов.
- Привязка к задаче (кампании): `campaigns.script_id` → `scripts.id`
- Привязка к контакту (опционально): `contacts.assigned_script_id` → `scripts.id`
- Тесты покрывают создание, обновление, удаление скриптов (`tests/test_api_scripts.py`).

### Human-like текст

**Статус: Готово (модуль humanizer)**

- **Модуль:** `app/core/humanizer.py`
- **Техники:**
  1. **Симуляция скорости печати:** `calculate_typing_delay(text)` — случайная скорость 200–350 символов/мин, задержка в ms.
  2. **Thinking delay:** `calculate_thinking_delay()` — 3–15 секунд перед ответом.
  3. **Self-correction:** `maybe_self_correct(text, rate=0.06)` — с вероятностью 6% добавляет префиксы «Точнее,», «Уточню,», «Поправка,».
  4. **Casual markers:** `add_casual_markers(text, rate=0.15)` — с вероятностью 15% вставляет «кстати», «слушайте», «если честно» в случайное предложение.
  5. **Double-take:** `maybe_double_take(text, city, rate=0.1)` — с вероятностью 10% задаёт вопрос про город («вы же говорите из {city}, там у вас, наверное, уже другие приоритеты?»).
  6. **Удаление markdown:** `remove_markdown()` — убирает `*`, `_`, `` ` ``, `#`.
- **Guardrails:** `app/llm/guardrails.py` — дополнительно блокирует markdown, повторы (>80% схожести), запрещённые слова («бот», «ассистент», «нейросеть»).

---

## Блок 4. Telegram-канал и отправка сообщений

### API: Bot API vs User API для cold outreach

**Статус: Реализовано через User API (MTProto / Pyrogram)**

- **Используется Pyrogram** (`app/bots/seller_client.py`) — User API (MTProto).
- **Bot API (aiogram)** используется **только** для Admin Bot (`app/bots/admin_bot.py`) — read-only уведомления, управление.
- **Cold outreach:** Да, реализован. User-аккаунты Telegram через MTProto могут писать первым по `telegram_user_id`.
- **Риск бана:** Учтён частично — есть rate limiting, daily limits, rotation аккаунтов, но нет полноценной системы анти-бана (прогрев аккаунтов реализован как скрипт-заглушка).

### Подключение и хранение credentials

- **Таблица:** `telegram_accounts` (`app/models/telegram_account.py`)
  ```sql
  id UUID PRIMARY KEY
  phone VARCHAR(20) UNIQUE NOT NULL
  session_string TEXT           -- Pyrogram session string
  display_name VARCHAR(100)
  username VARCHAR(32)
  bio TEXT
  avatar_url TEXT
  proxy_url TEXT
  status VARCHAR(20) DEFAULT 'warming'
  daily_messages_sent INTEGER DEFAULT 0
  last_message_at TIMESTAMPTZ
  cooldown_until TIMESTAMPTZ
  last_error TEXT
  ```
- **Шифрование:** `session_string` шифруется через Fernet (`cryptography`) при наличии `SESSION_ENCRYPTION_KEY` (`app/bots/seller_client.py:79-107`). Если ключ не задан — хранится plaintext.
- **API credentials:** `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` в `.env` (общие для всех аккаунтов).

### Исходящие сообщения (first message + personalization)

**Статус: Готово**

- **Формирование первого сообщения:** `send_initial_message()` в `app/core/scheduler.py:258-375`
  - LLM получает системный промпт (`build_system_prompt`) + user prompt с данными контакта: `first_name`, `company_name`, `position`, `city`, `industry`.
  - Генерация через `LLMEngine.generate_with_fallback()`.
  - Применяются guardrails + humanizer (typing delay, casual markers, self-correction).
  - Отправка через `SellerClient.send_message(user_id=contact.telegram_user_id, ...)`.
- **Персонализация:** Зависит от данных в импорте. Если `first_name`, `company_name` и т.д. заполнены — LLM использует их в промпте. Если нет — сообщение будет более обобщённым.

### Входящие сообщения

**Статус: Готово**

- **Механизм:** Long Polling через Pyrogram (`app/bots/inbound_listener.py`).
  - `start_inbound_listeners()` запускает Pyrogram Client для каждого `ready`/`active` аккаунта.
  - Регистрирует `@client.on_message` handler (`_handle_inbound_message`).
- **Webhook:** НЕ РЕАЛИЗОВАНО. Pyrogram работает через постоянное TCP-соединение с Telegram DC.
- **Гарантия доставки:** At-least-once на уровне БД (сообщение сохраняется перед обработкой LLM). Нет механизма retry при сбое LLM — сообщение просто не отвечается.

### Анти-спам / Rate Limiting

**Статус: Частично реализовано**

| Ограничение | Реализация | Статус |
|-------------|-----------|--------|
| 1 initial message + follow-up | `script.max_messages` (default 2) + `CampaignContact.message_count` | ✅ Готово |
| Интервал follow-up | `script.follow_up_delay_hours` (default 24ч) | ✅ Готово |
| Ограничение частоты на аккаунт | 1 сообщение в 30 секунд (`app/core/scheduler.py:218-226`) | ✅ Готово |
| Daily limit per account | `daily_message_limit` (default 50, `app/config.py:15`) + `account_manager.select_account()` | ✅ Готово |
| Рабочие часы | `is_within_working_hours()` в `app/core/scheduler.py:39-55` | ✅ Готово |
| Cooldown аккаунта | `account_manager.mark_account_cooldown()` — 24ч | ✅ Готово |
| Пауза между сообщениями в разные чаты | Нет глобальной очереди с backoff | ⚠️ Частично |

---

## Блок 5. LLM-диалог и интеграция

### Провайдер

**Статус: Готово (OpenRouter с fallback)**

- **Модуль:** `app/llm/engine.py`
- **Провайдер:** OpenRouter (`https://openrouter.ai/api/v1`)
- **Модели по умолчанию:**
  1. `qwen-2.5-72b-instruct`
  2. `gemini-2.5-flash-preview-05-20`
  3. `deepseek-chat`
- **Fallback:** `generate_with_fallback()` перебирает модели сверху вниз при ошибках.
- **Переключение моделей:** Через код — `LLMEngine.generate(messages, model=...)` или изменение `DEFAULT_MODELS`. В UI/Admin Bot переключение **не реализовано**.

### API-ключи

- **Хранение:** `.env` → `OPENROUTER_API_KEY` (`app/config.py:8`). Загружается через `pydantic-settings`.
- **Ротация / лимитирование по стоимости:** **НЕ РЕАЛИЗОВАНО**.
  - *Почему:* MVP, OpenRouter не требует сложного ротация ключей.
  - *Альтернатива:* Мониторить косты через OpenRouter Dashboard; при необходимости добавить таблицу `llm_api_keys` с ротацией.

### Контекст диалога

**Статус: Готово**

- **Хранение истории:** Таблица `messages` + `conversations`.
- **Передача в LLM:** `get_conversation_context()` (`app/services/conversation_service.py:20-70`) возвращает последние `limit=10` сообщений.
- **Кэш в Redis:** `cache_conversation_context()` / `get_cached_conversation_context()` (`app/db/redis.py:36-82`). TTL = 86400 сек. Инвалидируется при новом сообщении.
- **Ограничение длины:** Жёсткого токен-лимита нет, но передаётся только 10 последних сообщений. Для длинных диалогов возможен выход за лимит контекста модели.
- **State между сообщениями:** Хранится в `conversations.current_state` (state machine) и `conversations.facts_extracted` (JSON с фактами).

### Функции / Tools

**Статус: НЕ РЕАЛИЗОВАНО**

- ИИ возвращает **только текстовые ответы**. Нет function calling, tool use, structured output.
- «Записать на встречу» / «передать оператору» реализованы через:
  - **Классификацию интента** (`app/llm/intent_classifier.py`) — определяет `meeting_intent`.
  - **Уведомление оператору** (`app/services/notification_service.py`) — Telegram-уведомление в Admin Chat.
- *Почему:* MVP сфокусирован на текстовом диалоге. Function calling требует дополнительной архитектуры (календарь, CRM).
- *Альтернатива:* При `meeting_intent` оператор получает уведомление и сам договаривается о встрече.

---

## Блок 6. Воронка, статусы и квалификация

### Стадии воронки

**Статус: Готово (частично кастомизируемо)**

- **State Machine** (`app/core/state_machine.py`):
  - `cold` → `warm` → `hot` → `meeting_booked`
  - `follow_up` (промежуточное)
  - `objection_handler` (промежуточное)
  - `closed` (терминальное)
- **Кастомизация стадий:** Нет. Стадии hardcoded в `State` Literal. Скрипт не может добавить свои стадии.
- *Почему:* MVP, фиксированная воронка B2B.
- *Альтернатива:* Для MVP достаточно; расширение потребует рефакторинга state machine в динамическую конфигурацию (таблица `states` + `transitions`).

### Автоматическая квалификация

**Статус: Частично реализовано**

- **Критерии:**
  - Интент `meeting_intent` → перевод в `meeting_booked` (state machine) + уведомление оператору.
  - Интент `positive` → `hot`.
  - Интент `negative` → `closed`.
  - Интент `objection` → `objection_handler`.
- **Реализация:** `app/bots/inbound_listener.py:269-287` — `event_map` + `transition()` + обновление `sentiment`.

### Ручная квалификация

**Статус: Готово**

- **Интерфейс:** Admin Bot (Telegram)
  - Команда `/hotleads` — список диалогов в состоянии `hot` / `meeting_booked`.
  - Inline-кнопки: `✅ Qualified`, `❌ Rejected`, `📋 Диалог` (`app/bots/admin_bot.py:224-281`).
  - Обновляет `conversation.operator_status` (не `current_state`).
- **REST API:** `PUT /conversations/{id}/status` — обновление `operator_status` + `operator_notes` (`app/api/conversations.py:28`).

### Передача «горячего» лида

**Статус: Готово**

- **Механизм:** `NotificationService` (`app/services/notification_service.py`)
  - `send_hot_lead_alert()` — отправляет сообщение в `ADMIN_NOTIFICATION_CHAT_ID` с данными контакта, компании, последнего сообщения и inline-кнопкой «Посмотреть диалог».
  - `send_meeting_booked_alert()` — аналогично для встречи.
- **Статус в БД:** `conversation.current_state` = `hot` / `meeting_booked`, `conversation.operator_status` = `qualified`.

---

## Блок 7. Чат-интерфейс и БД

### Хранение данных

**Статус: Готово**

- **Тип БД:** PostgreSQL (реляционная), asyncpg + SQLAlchemy 2.0 Async.
- **Таблицы (миграция `alembic/versions/9fbbddc0c495_initial_migration.py`):**

| Таблица | Назначение | Связи |
|---------|-----------|-------|
| `scripts` | Скрипты продаж | — |
| `telegram_accounts` | User-аккаунты Telegram | — |
| `contacts` | База лидов | FK `assigned_script_id` → `scripts.id` |
| `campaigns` | Кампании (задачи) | FK `script_id` → `scripts.id` |
| `campaign_contacts` | Связь кампания-контакт (m2m) | FK `campaign_id`, `contact_id` |
| `conversations` | Диалоги | FK `contact_id`, `campaign_id` |
| `messages` | Сообщения | FK `conversation_id` |

### История сообщений

**Статус: Готово**

- **Таблица:** `messages`
  ```sql
  id UUID PRIMARY KEY
  conversation_id UUID FK → conversations.id
  direction VARCHAR(10)          -- 'inbound' / 'outbound'
  content TEXT NOT NULL
  message_type VARCHAR(20) DEFAULT 'text'
  intent_classification VARCHAR(50)
  llm_model VARCHAR(50)
  tokens_used INTEGER
  typing_delay_ms INTEGER
  sent_at TIMESTAMPTZ DEFAULT now()
  ```
- **Просмотр thread:**
  - REST API: `GET /conversations/{id}/messages` — полный thread с сортировкой по `sent_at`.
  - Admin Bot: `/conversations <contact_id>` или кнопка «📋 Диалог» в `/hotleads`.

### Интерфейс оператора

**Статус: Частично реализовано (только Telegram Bot)**

- **Веб-интерфейс:** **НЕ РЕАЛИЗОВАНО**. Нет React/Vue/HTML фронтенда.
- **Telegram-интерфейс (Admin Bot):**
  - `/hotleads` — список активных диалогов (`hot`, `meeting_booked`) с эмодзи-статусом, sentiment, последним сообщением.
  - `/conversations <contact_id>` — полный thread сообщений.
  - `/analytics` — dashboard метрики.
- *Почему:* MVP, быстрый доступ для заказчика через Telegram. Веб-интерфейс отложён.
- *Альтернатива:* Использовать Admin Bot для оперативного управления; расширить REST API для будущего фронтенда.

### Human Takeover

**Статус: НЕ РЕАЛИЗОВАНО**

- Оператор **не может** писать от имени ИИ/бота через систему.
- Доступные действия оператора:
  - Просмотр диалога (read-only).
  - Смена `operator_status` на `qualified` / `rejected`.
  - Получение уведомлений.
- *Почему:* Сложность реализации отправки сообщений через user-аккаунт из Admin Bot (нужна интеграция с `SellerClient`). MVP фокусируется на AI-диалоге.
- *Альтернатива:* Оператор вручную пишет лиду со своего личного Telegram, а в системе отмечает статус.

---

## Блок 8. Задачи (Campaigns / Tasks)

### Создание задачи

**Статус: Готово**

- **REST API:** `POST /campaigns` (`app/api/campaigns.py:39`)
  - Поля: `script_id`, `name`, `status` (default `draft`), `total_contacts`, etc.
- **Параметры задачи:**
  - `script_id` — выбор ИИ-менеджера (скрипта)
  - `contact_ids` — добавление через `POST /campaigns/{id}/contacts`
  - `status` — `draft` → `running` / `paused`
  - Время работы, интервал follow-up, max messages — наследуются из `Script`.

### Управление задачей

**Статус: Готово**

- **Кнопки:**
  - `POST /campaigns/{id}/start` — переводит `draft` → `running`, вызывает `process_campaigns()` для немедленной обработки.
  - `POST /campaigns/{id}/stop` — переводит `running` → `paused`.
- **Что происходит с запланированными сообщениями:**
  - Уже отправленные initial/follow-up не отзываются.
  - При `paused` scheduler перестаёт обрабатывать эту кампанию (`process_campaigns` фильтрует `status == 'running'`).
  - Нет отдельной очереди сообщений — они формируются на лету при запуске `process_campaigns`.

### Прогресс

**Статус: Частично реализовано**

- **Счётчики в кампании:**
  - `total_contacts` — всего добавлено
  - `processed_contacts` — обработано (отправлено хотя бы одно сообщение)
  - `replied_count` — ответили
  - `qualified_count` — квалифицировано
  - `meeting_booked_count` — встречи назначены
- **Статус «обработан»:** В текущей реализации счётчики обновляются при отправке (`send_initial_message`, `send_follow_up_message`), но нет явного инкремента `processed_contacts` в коде — поле есть в схеме, но его обновление не реализовано в `scheduler.py`.
  - *Альтернатива:* Использовать `COUNT(CampaignContact.status != 'pending')` для расчёта прогресса.

### Параллельные задачи

**Статус: Готово**

- Можно создать несколько кампаний с разными `script_id` и наборами контактов.
- `process_campaigns()` (`app/core/scheduler.py:115`) итерирует по ВСЕМ `running` кампаниям.
- Ограничение — shared pool аккаунтов Telegram и rate limit 1 msg / 30 sec per account.

---

## Блок 9. Рабочие часы и ограничения

### Рабочие часы

**Статус: Готово**

- **Реализация:** `is_within_working_hours()` в `app/core/scheduler.py:39-55`
- **Логика:** Сравнивает `now.time()` с `working_hours_start` и `working_hours_end` из скрипта.
- **По умолчанию:** 09:00–18:00 (`app/models/script.py:20-21`).
- **Отложенная отправка:** Нет явной очереди с доставкой "как только начнутся рабочие часы". Если `process_campaigns` запущен вне рабочих часов — кампания просто пропускается до следующего цикла (каждые 5 мин).

### Timezone

**Статус: Частично реализовано**

- Поле `script.timezone` хранится (default `Europe/Moscow`), но в `is_within_working_hours` оно **не используется для конвертации** — `now` передаётся как локальное время сервера (`datetime.now()`).
- *Почему:* MVP предполагает deployment в Москве; timezone-aware логика отложена.
- *Альтернатива:* Деплоить сервер в MSK или добавить `pytz`/`zoneinfo` конвертацию в `is_within_working_hours`.

### Опт-ин / Согласие / GDPR / 152-ФЗ

**Статус: НЕ РЕАЛИЗОВАНО**

- Нет механизма хранения согласия на коммуникацию.
- Нет механизма отписки (unsubscribe).
- Нет обработки запросов на удаление персональных данных.
- *Почему:* MVP для российского B2B-рынка, где базы часто собраны на основе публичных данных / договорных отношений. Для production требуется юридическая доработка.
- *Альтернатива:*
  1. Добавить флаг `opt_in` в `contacts`.
  2. Добавить в скрипт первое сообщение с запросом согласия.
  3. Хранить timestamp согласия.
  4. При получении «не пишите» — автоматически блокировать контакт (`status = 'unsubscribed'`).

---

## Блок 10. Аналитика и отчётность

### Отчёт по воронке

**Статус: Частично реализовано**

- **REST API:** `GET /analytics/dashboard` (`app/api/analytics.py:13`)
  - `total_contacts`
  - `campaigns_by_status` (группировка по статусам кампаний)
  - `reply_rate` (replied / total)
  - `qualified_count`
  - `meeting_booked_count`
- **Обновление:** В реальном времени (запрос к БД при каждом вызове).
- **По стадиям воронки (cold → warm → hot → meeting):** Нет явного breakdown. Есть только aggregate счётчики по кампаниям и hot leads.

### Эффективность (конверсия)

**Статус: Частично реализовано**

- **Метрики на уровне кампании:**
  - `reply_rate` = `SUM(replied_count) / SUM(total_contacts)`
  - `qualified_count`
  - `meeting_booked_count`
- **Где смотреть:** `/analytics/dashboard` (API) или `/analytics` (Admin Bot).
- **Недостаток:** Нет funnel conversion по шагам (sent → opened → replied → qualified → meeting). Нет разбивки по скриптам или аккаунтам.

### Экспорт отчётов

**Статус: НЕ РЕАЛИЗОВАНО**

- Нет endpoint для выгрузки CSV/PDF.
- *Альтернатива:* Использовать прямой доступ к БД или написать скрипт на pandas для выгрузки. Для MVP можно обойтись API + Admin Bot.

---

## Блок 11. Деплой, масштабирование и безопасность

### Production-ready

**Статус: Частично готово**

- **Docker / Docker Compose:** ✅ Готово (`Dockerfile`, `docker-compose.yml`)
- **Healthcheck:** ✅ `GET /health` в `app/main.py:56`
- **CI/CD:** **НЕ РЕАЛИЗОВАНО**. Нет GitHub Actions / GitLab CI файлов.
- **Мониторинг:** **НЕ РЕАЛИЗОВАНО**. Нет Prometheus / Grafana / Sentry.
- **Логирование:** Стандартный `logging` Python. Нет centralized logging (ELK / Loki).
- *Альтернатива:* Добавить `sentry-sdk` для трекинга ошибок; настроить `prometheus-fastapi-instrumentator`.

### Безопасность

**Статус: Частично реализовано**

| Аспект | Реализация | Статус |
|--------|-----------|--------|
| Шифрование токенов / API-ключей | Fernet для `session_string` (Pyrogram) | ✅ Частично |
| Хранение API-ключей | `.env` / env vars | ⚠️ Базово |
| HTTPS | Нет в коде; предполагается reverse proxy (nginx/traefik) | ⚠️ Инфраструктура |
| Доступ по ролям | Нет RBAC / авторизации. Admin Bot доступен всем, кто знает токен. REST API — open. | ❌ НЕ РЕАЛИЗОВАНО |
| SQL-инъекции | Защищено SQLAlchemy ORM + параметризованные запросы | ✅ |
| XSS / CSRF | FastAPI + Pydantic валидация входных данных | ✅ Базово |

- *Почему нет RBAC:* MVP, один пользователь (заказчик).
- *Альтернатива:* Добавить `Authorization: Bearer <token>` middleware в FastAPI; привязать Admin Bot к `chat_id` whitelist.

### Масштабирование

**Статус: Частично готово**

| Масштаб | Оценка | Комментарий |
|---------|--------|-------------|
| 100 контактов | ✅ Без проблем | Одна кампания, 1-2 аккаунта |
| 1 000 контактов | ⚠️ Нужен контроль | `process_campaigns` раз в 5 мин может не успевать обработать всех из-за rate limit (1 msg / 30 sec) и LLM latency (~1-3 сек). |
| 10 000 контактов | ❌ Не готово | Нет горизонтального масштабирования шедулера. Нет Celery / RQ / SQS. Redis используется только для кэша. |

- **Очереди:** Redis есть, но как брокер сообщений **не используется**. `APScheduler` + polling БД — это не очередь.
- *Альтернатива:*
  1. Добавить **Celery + Redis** для async tasks (отправка сообщений, вызов LLM).
  2. Разделить `scheduler` на producer (добавляет задачи в очередь) и workers (консьюмеры отправляют сообщения).
  3. Для 10k+ контактов — горизонтальное масштабирование workers.

---

## Финальный вопрос для разработчиков — Сводка «НЕ РЕАЛИЗОВАНО»

| # | Требование | Почему не реализовано | Когда планируется | Альтернатива прямо сейчас |
|---|-----------|----------------------|-------------------|---------------------------|
| 1 | **Дедупликация контактов при импорте** | Сроки MVP, сложная логика fuzzy matching | Спринт 3 | Предварительная очистка CSV вручную |
| 2 | **Парсинг контактов (Rosprofile и др.)** | Вне скоупа MVP, юридические риски | Не планируется в MVP | Импорт готовых баз |
| 3 | **Webhook для входящих сообщений** | Pyrogram использует Long Polling (MTProto TCP) | Не планируется | Long Polling стабилен |
| 4 | **Function calling / Tools (запись на встречу, CRM)** | Сложность интеграции с календарями | Спринт 4 | Уведомление оператору + ручная запись |
| 5 | **Веб-интерфейс оператора** | MVP фокус на Telegram Bot | Спринт 4-5 | Admin Bot |
| 6 | **Human Takeover (писать от имени ИИ)** | Архитектурная сложность, безопасность | Спринт 4 | Оператор пишет с личного Telegram |
| 7 | **Экспорт отчётов (CSV/PDF)** | Низкий приоритет для MVP | Спринт 3 | Прямой доступ к PostgreSQL |
| 8 | **GDPR / 152-ФЗ / Opt-in / Отписка** | Требует юридической проработки | До production | Добавить disclaimer в скрипт + ручная блокировка |
| 9 | **Timezone-aware рабочие часы** | Сервер планируется в MSK | Спринт 3 | Деплой в MSK |
| 10 | **RBAC / Аутентификация в API** | Один пользователь в MVP | Спринт 3 | Ограничить доступ по IP / VPN |
| 11 | **CI/CD, мониторинг, centralized logging** | Инфраструктурные задачи | Спринт 3 | Ручной деплой + docker logs |
| 12 | **Горизонтальное масштабирование (>1k контактов)** | Требует Celery / SQS | Спринт 4 | Увеличение количества аккаунтов + регулировка интервалов |
| 13 | **Полноценный прогрев аккаунтов** | Скрипт `warmup_accounts.py` — заглушка | Спринт 2-3 | Ручной прогрев через телефоны |
| 14 | **Переключение LLM-моделей в UI** | Низкий приоритет | Спринт 3 | Изменение `DEFAULT_MODELS` в коде |

---

## Приложение: Полный список файлов проекта (ключевые)

```
app/
├── main.py                    # FastAPI entrypoint, lifespan (scheduler + bots)
├── config.py                  # Pydantic Settings (.env)
├── api/
│   ├── scripts.py             # CRUD /scripts
│   ├── campaigns.py           # CRUD /campaigns + start/stop/add contacts
│   ├── contacts.py            # CRUD /contacts + /contacts/import
│   ├── conversations.py       # GET /conversations + messages + status update
│   └── analytics.py           # GET /analytics/dashboard
├── bots/
│   ├── admin_bot.py           # aiogram Admin Bot (commands, FSM)
│   ├── inbound_listener.py    # Pyrogram inbound handler
│   └── seller_client.py       # Pyrogram MTProto client wrapper
├── core/
│   ├── scheduler.py           # APScheduler + process_campaigns + send_initial/follow_up
│   ├── state_machine.py       # Lead funnel transitions
│   ├── humanizer.py           # Typing delays, casual markers, markdown removal
│   └── account_manager.py     # Account rotation, daily limits, cooldown
├── llm/
│   ├── engine.py              # OpenRouter client + fallback + guardrails wrapper
│   ├── prompts.py             # System & user prompt builders
│   ├── guardrails.py          # Anti-repetition, anti-bot-words, anti-markdown
│   └── intent_classifier.py   # LLM-based intent classification
├── services/
│   ├── contact_import.py      # CSV/Excel parsing (pandas)
│   ├── conversation_service.py # Context retrieval, message persistence, facts
│   └── notification_service.py # Telegram alerts for hot leads / meetings
├── db/
│   ├── session.py             # SQLAlchemy async engine & session
│   └── redis.py               # Redis connection + conversation cache
├── models/
│   ├── script.py
│   ├── contact.py
│   ├── campaign.py
│   ├── conversation.py
│   └── telegram_account.py
└── schemas/
    ├── script.py
    ├── contact.py
    ├── campaign.py
    └── conversation.py

tests/                         # 22 тестовых файла, покрытие API, core, LLM, bots, services
alembic/versions/9fbbddc0c495_initial_migration.py
scripts/
├── import_contacts.py         # CLI import
└── warmup_accounts.py         # Account warm-up stub
docker-compose.yml             # postgres + redis + api + scheduler + admin-bot
Dockerfile
requirements.txt
.env.example
pytest.ini
```

---

*Документ подготовлен на основе полного анализа кодовой базы репозитория `ai-sales-manager`.*
