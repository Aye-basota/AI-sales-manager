# AI Sales Manager

Система автоматизации B2B outbound продаж через Telegram с использованием живых аккаунтов (MTProto) и LLM для human-like коммуникации.

Построена для автономной работы: запустил кампанию — система сама отправляет первичные сообщения, обрабатывает ответы, ведет диалог, назначает встречи и уведомляет оператора о горячих лидах.

## Для заказчика и ревьюера

- **Доступ к продукту:** с Sprint 4 (Week 6) продукт развёрнут на постоянном production VPS (не только по запросу через Docker Compose / localtunnel, как раньше). Публичный адрес VPS не публикуется в этом репозитории из соображений безопасности живого Telegram-аккаунта — доступ предоставляется напрямую заказчику и проверяющим через приватный канал сдачи задания. Актуальный статус и инструкции: [`docs/customer-handover.md`](docs/customer-handover.md).
- **Документация:** [hosted docs site](https://aye-basota.github.io/AI-sales-manager/)
- **Handover / статус передачи проекта:** [`docs/customer-handover.md`](docs/customer-handover.md)
- **Как контрибьютить:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Инструкции для AI-агентов:** [`AGENTS.md`](AGENTS.md)
- **Быстрый запуск:** см. [«Быстрый старт (Docker)»](#быстрый-старт-docker) ниже или подробный гид [`LAUNCH_GUIDE.md`](LAUNCH_GUIDE.md)

---

## Промо-сайт для заказчиков

В директории `site/` размещён самостоятельный промо-лендинг, который можно показывать потенциальным заказчикам.

- **Локальный просмотр:** откройте `site/index.html` в браузере или запустите `python -m http.server --directory site`.
- **Встроенная раздача через FastAPI:** при запуске приложения лендинг автоматически доступен по корневому URL `http://localhost:8000/`. API-эндпоинты (`/docs`, `/health`, `/scripts` и др.) продолжают работать как раньше.

Лендинг адаптирован под мобильные устройства, содержит блоки преимуществ, воронки, тарифов, FAQ и форму захвата заявок.

---

## Документация проекта

Поддерживаемая техническая документация опубликована на GitHub Pages:

- **[AI Sales Manager Docs](https://aye-basota.github.io/AI-sales-manager/)** — hosted documentation site

Ключевые файлы документации в репозитории:
- [`docs/customer-handover.md`](docs/customer-handover.md) — актуальный статус передачи проекта заказчику
- [`docs/roadmap.md`](docs/roadmap.md) — Sprint-by-Sprint план поставки
- [`docs/architecture/README.md`](docs/architecture/README.md) — архитектура системы (static / dynamic / deployment views)
- [`docs/development-process.md`](docs/development-process.md) — процесс разработки, git workflow и управление конфигурацией
- [`docs/definition-of-done.md`](docs/definition-of-done.md) — Definition of Done
- [`docs/testing.md`](docs/testing.md) — стратегия тестирования
- [`docs/quality-requirements.md`](docs/quality-requirements.md) — quality requirements (ISO/IEC 25010)
- [`docs/quality-requirement-tests.md`](docs/quality-requirement-tests.md) — автоматизированные QRTs
- [`docs/user-acceptance-tests.md`](docs/user-acceptance-tests.md) — UAT сценарии
- [`docs/interface.md`](docs/interface.md) — интерфейсная спецификация
- [`docs/user-stories.md`](docs/user-stories.md) — реестр user stories
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — как контрибьютить в проект
- [`AGENTS.md`](AGENTS.md) — инструкции для AI-агентов, работающих в этом репозитории

---

## Содержание

- [Для заказчика и ревьюера](#для-заказчика-и-ревьюера)
- [Промо-сайт для заказчиков](#промо-сайт-для-заказчиков)
- [Документация проекта](#документация-проекта)
- [Ключевые возможности](#ключевые-возможности)
- [Архитектура и потоки данных](#архитектура-и-потоки-данных)
  - [Outbound: запуск кампании](#outbound-запуск-кампании)
  - [Inbound: обработка ответов](#inbound-обработка-ответов)
  - [State Machine](#state-machine)
  - [Автономность и отказоустойчивость](#автономность-и-отказоустойчивость)
- [Стек технологий](#стек-технологий)
- [Требования](#требования)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Локальная разработка](#локальная-разработка)
- [Переменные окружения](#переменные-окружения)
- [Admin Bot](#admin-bot)
- [Lead Discovery](#lead-discovery)
- [Тестирование](#тестирование)
- [Известные ограничения](#известные-ограничения)
- [Roadmap](#roadmap)
- [Лицензия](#лицензия)

---

## Ключевые возможности

- **Живые Telegram-аккаунты** — отправка через Pyrogram (MTProto), а не Bot API. Сообщения приходят от реальных пользователей.
- **LLM-диалоги** — генерация ответов через OpenRouter (Qwen / Gemini / DeepSeek) или DashScope (Qwen) с guardrails (защита от markdown, признаков бота, повторов).
- **Humanizer** — имитация человеческого поведения: задержки печати, паузы "на подумать", случайные разговорные вставки, самокоррекция.
- **Скрипты и кампании** — гибкие скрипты продаж с настройкой тона, рабочих часов, таймзоны, follow-up задержки.
- **Anti-spam** — rotation аккаунтов, cooldown при FloodWait/PeerFlood, daily limits, rate limit 1 сообщение / 30 сек на аккаунт.
- **Автоматическая воронка** — initial → follow-up (24ч) → auto-close (48ч). State machine управляет состоянием диалога.
- **Lead-nurturing sales funnel** — 5 этапов (trust → engagement → qualification → value → CTA), конфигурируемые через API или Script.
- **Загрузка воронки через API** — preview / upload JSON или plain-text funnel definitions (`POST /api/funnels/preview`, `POST /api/funnels/upload`).
- **Версионирование промптов** — внешний JSON-конфиг `app/config/prompts/v1.json`, обновляется без изменения кода.
- **AI-automation rate** — метрика доли диалогов, обработанных без эскалации оператору (`GET /analytics/automation-rate`).
- **Мониторинг продакшена** — `/health`, structured logging (`LOG_LEVEL`), Docker health checks и restart policies.
- **Hot Lead alerts** — мгновенные уведомления оператору при согласии на созвон / положительном ответе.
- **Lead Discovery** — поиск контактов через Telegram Search, парсинг каналов, внешние API.
- **Аналитика** — дашборд с reply rate, hot leads, meetings booked.

---

## Архитектура и потоки данных

### Outbound: запуск кампании

```
Пользователь (/startcampaign или API)
  ↓
Campaign.status = "running"
  ↓
APScheduler (каждые 5 мин) → process_campaigns()
  ↓
Загрузка CampaignContact (status: pending / initial_sent)
  ↓
Фильтр: working_hours (timezone-aware), follow_up_delay, max_messages
  ↓
Выбор TelegramAccount (ready/active, session_string != null,
                        daily_messages_sent < 50, rate_limit 30с)
  ↓
Генерация сообщения (LLM + guardrails + humanizer)
  ↓
Отправка через SellerClient (Pyrogram)
  ↓
При FloodWait / PeerFlood → mark_account_cooldown → retry с другим аккаунтом
  ↓
Обновление БД: CampaignContact, Conversation, Message, Account, Campaign
```

### Inbound: обработка ответов

```
Inbound сообщение (Pyrogram listener, no_updates=False)
  ↓
Поиск / создание Contact по telegram_user_id
  ↓
Поиск Conversation → создание при необходимости
  ↓
Сохранение inbound Message
  ↓
Обновление CampaignContact.status = "replied"
  ↓
Проверка campaign.status == "running" (иначе автоответ не отправляется)
  ↓
Classify intent (meeting_intent / positive / negative / objection / informational)
  ↓
Генерация ответа (LLM + история + facts + guardrails + fallback)
  ↓
Humanizer (typing + thinking delay) → send_message
  ↓
Сохранение outbound Message + обновление Conversation.state
  ↓
Если intent == "meeting_intent" или state == "hot" → уведомление оператору
```

### State Machine

| Состояние | Событие | Новое состояние |
|-----------|---------|-----------------|
| cold | initial_message | warm |
| cold/warm/hot | no_reply_24h | follow_up |
| cold/warm/hot | no_reply_48h | closed |
| any | positive_reply | hot |
| any | negative_reply | closed |
| any | meeting_intent | meeting_booked |
| any | objection | objection_handler |
| any | informational | *без изменений* |

Terminal states: `meeting_booked`, `closed` — дальнейшие сообщения не отправляются.

### Автономность и отказоустойчивость

| Механизм | Описание |
|----------|----------|
| **APScheduler + SQLAlchemyJobStore** | Задачи persistent. После перезагрузки сервера scheduler восстанавливает расписание. |
| **process_campaigns** | Каждые 5 мин. Обрабатывает только `running` кампании в рабочие часы. |
| **reset_daily_counters** | Cron 00:00 Europe/Moscow. Сбрасывает `daily_messages_sent` для всех аккаунтов. |
| **recover_cooldown_accounts** | Каждые 6 часов. Возвращает аккаунты из `cooldown` в `ready`, если `cooldown_until <= now()`. |
| **auto_close_conversations** | Каждые 6 часов. Закрывает `follow_up_sent` старше 48ч. |
| **SellerClient heartbeat** | Каждые 30 сек проверяет соединение Pyrogram. При разрыве — exponential backoff reconnect. |
| **LLM fallback** | 3 модели в cascade (Qwen → Gemini → DeepSeek). При отказе всех — fallback text. |
| **Guardrails retry** | При reject guardrails — повторная генерация с strict prompt. Если снова fail — fallback text. |

---

## Стек технологий

- **Backend:** Python 3.11+, FastAPI 0.138, Pydantic 2.13
- **База данных:** PostgreSQL 15+, SQLAlchemy 2.0 (async), Alembic
- **Кэш / очереди:** Redis 7+
- **Telegram:** Pyrogram 2.0 (MTProto user client), aiogram 3.29 (Admin Bot)
- **Планировщик:** APScheduler 3.11 (SQLAlchemyJobStore)
- **LLM:** OpenRouter API + DashScope (Alibaba Cloud), OpenAI-compatible fallback cascade
- **Тестирование:** pytest, pytest-asyncio, pytest-mock, faker, bandit, pip-audit
- **DevOps:** Docker, Docker Compose, GitHub Actions (CI, docs, link check, security audit)
- **Документация:** MkDocs Material, GitHub Pages

---

## Требования

- Docker + Docker Compose (для продакшена)
- Или Python 3.11+ + PostgreSQL + Redis (для разработки)
- Telegram API ID / API Hash (https://my.telegram.org)
- OpenRouter API Key (https://openrouter.ai) **или** DashScope API Key (https://dashscope-intl.aliyuncs.com)
- Telegram Bot Token для Admin Bot (https://t.me/BotFather)

---

## Быстрый старт (Docker)

Этот путь — основной. Он поднимает PostgreSQL, Redis, API, scheduler, Admin Bot polling и inbound listener в контейнерах.

```bash
# 1. Подготовь env
cp .env.example .env

# 2. Сгенерируй ключ для шифрования Telegram session string
docker compose run --rm api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. Заполни .env:
# ADMIN_BOT_TOKEN=...
# ADMIN_NOTIFICATION_CHAT_ID=...
# TELEGRAM_API_ID=...
# TELEGRAM_API_HASH=...
# SESSION_ENCRYPTION_KEY=<результат команды выше>
# SELLER_PHONE=+79991234567
# DASHSCOPE_API_KEY=... или OPENROUTER_API_KEY=...

# 4. Собери и запусти сервисы
docker compose up -d --build

# 5. Примени миграции БД
docker compose exec -T api alembic upgrade head

# 6. Проверь, что API, scheduler, db и admin bot живы
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok","scheduler":true,"db":true,"admin_bot":true}
```

Приложение поднимется на `http://localhost:8000`.

- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Admin Bot: бот из `ADMIN_BOT_TOKEN`

Полезные команды:

```bash
docker compose ps
docker compose logs -f api
docker compose restart api
docker compose down
```

### Демо-данные для презентаций

Чтобы в интерфейсе не было пустых списков во время демо, запустите seed-скрипт:

```bash
docker compose exec -T api python scripts/seed_demo_data.py
```

Скрипт создаёт демо-скрипт, 5 демо-контактов с компаниями, запущенную кампанию и несколько диалогов с ответами (включая hot lead).

### Session String для Telegram seller-аккаунта

Чтобы система могла отправлять сообщения от живого Telegram-аккаунта, нужно получить `session string`.

```bash
# Заполни в .env номер seller-аккаунта
# SELLER_PHONE=+79991234567

# Перезапусти контейнеры, чтобы подхватить .env
docker compose restart api

# Запусти генератор session string
docker compose exec api python scripts/generate_session.py
```

Скрипт попросит код подтверждения. В другом терминале выполни:

```bash
docker compose exec api bash -c "echo 12345 > /tmp/telegram_code.txt"
```

(замени `12345` на реальный код из SMS или Telegram).

В конце скрипт выведет длинную строку — это `session string`. Добавь аккаунт в систему через Swagger (`http://localhost:8000/docs` → `POST /telegram-accounts`) или curl:

```bash
curl -X POST "http://localhost:8000/telegram-accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+79991234567",
    "session_string": "ВАША_SESSION_STRING",
    "username": "your_seller_username",
    "status": "ready"
  }'
```

Проверь, что аккаунт готов:

```bash
curl http://localhost:8000/telegram-accounts
```

> Подробный пошаговый гид с созданием скриптов, кампаний и первой отправкой — в [`LAUNCH_GUIDE.md`](LAUNCH_GUIDE.md).

### Быстрый тест Upload

В репозитории есть тестовый файл для ручной проверки импорта:

```text
test_leads_upload.csv
```

Он содержит 2 контакта в формате, который принимает Admin Bot. Для проверки открой Admin Bot → `/upload` → отправь `test_leads_upload.csv` → выбери бизнес → проверь первое сообщение → запусти или сохрани черновик.

Важно: для первого сообщения через MTProto одного numeric `telegram_user_id` обычно недостаточно, если seller-аккаунт раньше не видел этого пользователя. Надежнее указывать `telegram_username`; raw id сработает только для уже известного peer или после входящего сообщения от лида.

---

## Локальная разработка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Настрой окружение
cp .env.example .env

# Примени миграции
alembic upgrade head

# Запусти сервер
uvicorn app.main:app --reload

# Запусти тесты
pytest tests/ -v
```

---

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DATABASE_URL` | PostgreSQL async URL | `postgresql+asyncpg://sales:salespass@localhost:5432/ai_sales` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | Провайдер LLM | `openrouter` / `dashscope` |
| `OPENROUTER_API_KEY` | Ключ OpenRouter | `sk-or-v1-...` |
| `OPENROUTER_BASE_URL` | OpenRouter-совместимый endpoint | `https://openrouter.ai/api/v1` |
| `DASHSCOPE_API_KEY` | Ключ DashScope (Alibaba Cloud) | `sk-ws-...` |
| `DASHSCOPE_BASE_URL` | DashScope endpoint | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| `ADMIN_BOT_TOKEN` | Токен Telegram Bot для admin панели | `123456:ABC...` |
| `ADMIN_NOTIFICATION_CHAT_ID` | Chat ID для hot lead alerts | `-1001234567890` |
| `SECRET_KEY` | Секрет для JWT / криптографии | `changeme` |
| `SESSION_ENCRYPTION_KEY` | Fernet ключ для шифрования session_string | `base64...=` |
| `TELEGRAM_API_ID` | App ID из my.telegram.org | `12345` |
| `TELEGRAM_API_HASH` | App Hash из my.telegram.org | `abc...` |
| `SELLER_PHONE` | Номер Telegram seller-аккаунта для генерации session string | `+79991234567` |
| `DAILY_MESSAGE_LIMIT` | Лимит сообщений в сутки на аккаунт | `50` |
| `DEBUG` | Режим отладки | `True` / `False` |
| `LOG_LEVEL` | Уровень логирования (INFO, DEBUG, WARNING, ERROR) | `INFO` |

---

## Admin Bot

Admin Bot управляет системой через Telegram.

| Команда | Описание |
|---------|----------|
| `/start` | Список доступных команд |
| `/scripts` | Список скриптов |
| `/newscript` | Создание скрипта по шагам (FSM) |
| `/campaigns` | Список кампаний с кнопками Pause / Resume / Stop |
| `/startcampaign` | Запуск кампании из статуса draft |
| `/upload` | Импорт контактов из CSV / Excel + создание кампании |
| `/discover` | Поиск лидов через публичные сообщения Telegram (MTProto `search_global`) |
| `/analytics` | Дашборд метрик |
| `/hotleads` | Список hot leads и meeting booked с кнопками Qualified / Rejected |
| `/conversations <contact_id>` | История диалога |

---

## Funnel API

Воронки продаж можно задавать не только через Admin Bot, но и через API:

```bash
# Проверить / спревьюить funnel без сохранения
curl -X POST "http://localhost:8000/api/funnels/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nurturing Funnel",
    "format": "json",
    "content": "{\"stages\":[{\"stage\":\"trust\",\"goal\":\"Build trust\",\"max_length\":200},{\"stage\":\"cta\",\"goal\":\"Close\",\"max_length\":400,\"allow_call_to_action\":true}]}"
  }'

# Загрузить funnel и привязать к кампании
curl -X POST "http://localhost:8000/api/funnels/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nurturing Funnel",
    "format": "json",
    "campaign_id": "<campaign-uuid>",
    "content": "<funnel-json>"
  }'
```

Поддерживаются форматы `json` и `text`. Для запущенной кампании перезапись требует `force: true`.

## Production Monitoring

- **Health check:** `GET /health` возвращает `status`, `db`, `scheduler`.
- **Uptime monitoring:** используйте `GET /health` как endpoint для UptimeRobot / Grafana.
- **Логи:** все сервисы пишут в stderr в формате `timestamp | level | name | message`. Уровень задаётся `LOG_LEVEL`.
- **Restart policy:** `restart: unless-stopped` для postgres, redis, api в `docker-compose.yml`.

## Lead Discovery

MVP-поиск лидов работает без платных каталогов. Система использует официальный Telegram MTProto API через подключенный seller-аккаунт:

1. Admin Bot спрашивает описание бизнеса, целевую аудиторию, страну, язык, признаки потребности и лимит.
2. Система строит локальные и английские поисковые запросы.
3. Pyrogram вызывает глобальный поиск публичных сообщений Telegram (`search_global`).
4. Система анализирует найденные сообщения, отбрасывает рекламу/вакансии/мусор и берет только сообщения из публичных групп/чатов.
5. Из видимого автора сообщения сохраняются `telegram_user_id`, username, имя, ссылка на сообщение, текст сообщения и краткий контекст.
6. На выходе Admin Bot отправляет `telegram_leads.csv`, совместимый с `/upload`.

Ограничения Telegram:

- можно получить авторов видимых публичных сообщений;
- нельзя получить подписчиков обычного канала, если они не писали публично;
- качество результата зависит от ключевых слов, языка, страны и доступности публичных обсуждений;
- для поиска нужен ready/active seller-аккаунт с session string.

CSV из поиска можно сразу сохранить как контакты или загрузить вручную через `/upload`.

---

## Тестирование

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

**Текущий полный прогон:** `695 passed, 3 warnings`.

Ключевые модули с высоким покрытием:
- `app/core/state_machine.py` — 100%
- `app/api/analytics.py` — 100%
- `app/api/conversations.py` — 100%
- `app/api/health.py` — 100%
- `app/llm/engine.py` — 94%
- `app/services/notification_service.py` — 94%

Автоматизированные Quality Requirement Tests (QRTs) находятся в `tests/quality_requirement_tests/` и проверяют:
- latency health endpoint (QRT-001),
- availability health endpoint (QRT-002),
- fault tolerance API на невалидном JSON (QRT-003).

CI также запускает `bandit` (security), `pip-audit` (dependency vulnerabilities), `flake8` (lint) и `lychee` (link check).

### Smoke-check после деплоя

```bash
docker compose ps
curl http://localhost:8000/health
docker compose logs --since=10m api | grep -E "ERROR|Traceback|MissingGreenlet" || true
docker compose exec -T api python scripts/admin_ux_lab.py
```

Если Docker daemon не запущен, бот не будет отвечать: сначала запусти Docker Desktop / Docker service, затем `docker compose up -d`.

### Если Admin Bot не отвечает

1. Проверь Docker: `docker compose ps`.
2. Проверь health: `curl http://localhost:8000/health`.
3. Проверь, что `admin_bot=true`.
4. Посмотри логи: `docker compose logs --since=10m api`.
5. Убедись, что `ADMIN_BOT_TOKEN` верный и нет второго процесса, который polling-ит того же бота.
6. Перезапусти API: `docker compose restart api`.

### Если кампания не отправляет сообщения

Проверь:

- рабочие часы бизнеса и timezone;
- статус кампании `running`;
- что есть pending contacts;
- что seller-аккаунт `ready`/`active`;
- `DAILY_MESSAGE_LIMIT` и `daily_messages_sent`;
- логи scheduler: `docker compose logs --since=30m api | grep "Skipping campaign"`.

---

## Известные ограничения

Ниже перечислены нюансы, выявленные при аудите. Они **не блокируют** запуск, но стоит иметь их в виду.

### P1.1: Inbound flood → бан аккаунта

- **Риск:** Если лид напишет 10 сообщений подряд, аккаунт ответит на все, превысит daily limit и уйдет в cooldown.
- **Реальность:** В B2B outreach люди редко пишут 10 сообщений подряд. Обычно 1–2. Это крайний случай.
- **Решение:** Добавить `if account.daily_messages_sent >= limit: skip` в `inbound_listener.py` — 5 строк.

### P1.2: Race condition → double reply

- **Риск:** Если лид напишет 2 сообщения за 1 секунду, бот теоретически может ответить дважды.
- **Реальность:** Telegram не доставляет сообщения мгновенно. Pyrogram обрабатывает их последовательно в одном event loop. Вероятность реального race condition низкая.
- **Решение:** Redis lock на `conversation_id` — ~10 строк, можно отложить до первых реальных случаев.

### ✅ P1.3: Метрики засоряются для paused/closed кампаний

- **Риск:** Аналитика показывает «ответы» по неактивным (paused/closed) кампаниям.
- **Статус:** Исправлено. Обновление `campaign.replied_count` и `CampaignContact.status = "replied"` теперь выполняется только для кампаний со статусом `running`.

### ✅ P2: `processed_contacts` считает сообщения, а не уникальные контакты

- **Риск:** Если 5 контактов получили initial + follow-up, в UI отобразится `10/10` вместо `5/10`. Семантически неверно.
- **Статус:** Исправлено. `processed_contacts` увеличивается только при первом исходящем сообщении контакту.

### ✅ P2: `assigned_account_id` без проверки статуса

- **Риск:** Если контакт закреплен за аккаунтом в `cooldown` или без `session_string`, система пыталась использовать его и падала.
- **Статус:** Исправлено. Перед использованием закреплённого аккаунта проверяется его eligibility (статус, наличие session string, cooldown); при непрохождении выполняется fallback на любой доступный аккаунт.

---

## Roadmap

- [ ] Inbound rate limit & daily limit guard
- [ ] Redis distributed lock для `conversation_id`
- [ ] Ручной takeover диалога оператором (`is_paused_by_operator`)
- [ ] Funnel-аналитика по стадиям
- [x] Учет `processed_contacts` по уникальным контактам, а не сообщениям
- [ ] Поддержка голосовых сообщений и фото
- [ ] Автоматическая интеграция с календарем (Google Calendar / Calendly) при `meeting_intent`
- [ ] A/B тестирование скриптов
- [ ] WebSocket real-time dashboard

Подробнее см. [`docs/roadmap.md`](docs/roadmap.md).

---

## Лицензия

[MIT](LICENSE) — AI Sales Manager contributors.
