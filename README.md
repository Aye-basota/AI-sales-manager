# AI Sales Manager

Система автоматизации B2B outbound продаж через Telegram с использованием живых аккаунтов (MTProto) и LLM для human-like коммуникации.

Построена для автономной работы: запустил кампанию — система сама отправляет первичные сообщения, обрабатывает ответы, ведет диалог, назначает встречи и уведомляет оператора о горячих лидах.

---

## Промо-сайт для заказчиков

В директории `site/` размещён самостоятельный промо-лендинг, который можно показывать потенциальным заказчикам.

- **Локальный просмотр:** откройте `site/index.html` в браузере или запустите `python -m http.server --directory site`.
- **Встроенная раздача через FastAPI:** при запуске приложения лендинг автоматически доступен по корневому URL `http://localhost:8000/`. API-эндпоинты (`/docs`, `/health`, `/scripts` и др.) продолжают работать как раньше.

Лендинг адаптирован под мобильные устройства, содержит блоки преимуществ, воронки, тарифов, FAQ и форму захвата заявок.

---

## Содержание

- [Промо-сайт для заказчиков](#промо-сайт-для-заказчиков)
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
- **Конфигурируемая sales funnel** — 4 этапа (hook → qualification → value → CTA), настраиваемые через Script и отслеживаемые в Conversation.
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

- **Backend:** Python 3.11+, FastAPI 0.111, Pydantic 2.7
- **База данных:** PostgreSQL 15+, SQLAlchemy 2.0 (async), Alembic
- **Кэш / очереди:** Redis 7+
- **Telegram:** Pyrogram 2.0 (MTProto user client), aiogram 3.6 (Admin Bot)
- **Планировщик:** APScheduler 3.10 (SQLAlchemyJobStore)
- **LLM:** OpenRouter API + DashScope (Alibaba Cloud), OpenAI-compatible fallback cascade
- **Тестирование:** pytest, pytest-asyncio, pytest-mock, faker
- **DevOps:** Docker, Docker Compose

---

## Требования

- Docker + Docker Compose (для продакшена)
- Или Python 3.11+ + PostgreSQL + Redis (для разработки)
- Telegram API ID / API Hash (https://my.telegram.org)
- OpenRouter API Key (https://openrouter.ai) **или** DashScope API Key (https://dashscope-intl.aliyuncs.com)
- Telegram Bot Token для Admin Bot (https://t.me/BotFather)

---

## Быстрый старт (Docker)

```bash
# 1. Скопируй и заполни .env
cp .env.example .env
# Отредактируй .env — добавь:
#   TELEGRAM_API_ID, TELEGRAM_API_HASH (https://my.telegram.org)
#   ADMIN_BOT_TOKEN (https://t.me/BotFather)
#   DASHSCOPE_API_KEY (или OPENROUTER_API_KEY)
#   SESSION_ENCRYPTION_KEY (см. раздел "Session String")

# 2. Собери и запусти сервисы
docker-compose up -d --build

# 3. Примени миграции БД
docker-compose exec api alembic upgrade head

# 4. Проверь, что API работает
curl http://localhost:8000/health
```

Приложение поднимется на `http://localhost:8000`.

- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Session String для Telegram seller-аккаунта

Чтобы система могла отправлять сообщения от живого Telegram-аккаунта, нужно получить `session string`.

```bash
# Заполни в .env номер seller-аккаунта
# SELLER_PHONE=+79991234567

# Сгенерируй ключ шифрования (если ещё не сделал)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Скопируй результат в SESSION_ENCRYPTION_KEY в .env

# Перезапусти контейнеры, чтобы подхватить .env
docker-compose restart

# Запусти генератор session string
docker-compose exec api python scripts/generate_session.py
```

Скрипт попросит код подтверждения. В другом терминале выполни:

```bash
docker-compose exec api bash -c "echo 12345 > /tmp/telegram_code.txt"
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

> Подробный пошаговый гид с созданием скриптов, кампаний и первой отправкой — в [`LAUNCH_GUIDE.md`](LAUNCH_GUIDE.md).

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
| `DAILY_MESSAGE_LIMIT` | Лимит сообщений в сутки на аккаунт | `50` |
| `DEBUG` | Режим отладки | `True` / `False` |

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
| `/discover` | Поиск лидов (Telegram Search / Channels / External API) |
| `/analytics` | Дашборд метрик |
| `/hotleads` | Список hot leads и meeting booked с кнопками Qualified / Rejected |
| `/conversations <contact_id>` | История диалога |

---

## Lead Discovery

Источники поиска контактов:

- **Telegram Search** — глобальный поиск публичных пользователей по ключевому слову.
- **Channel Parse** — парсинг участников канала/группы с фильтрацией по ключевым словам в профиле.
- **External API** — generic JSON adapter для внешних баз (например, Rosprofile). Требует `EXTERNAL_LEAD_API_URL`.

Найденные контакты проходят валидацию (`validate_and_enrich`) через Pyrogram `get_users` — проверяется существование username, заполняется `telegram_user_id`, `is_valid`. Дедупликация при импорте по `telegram_username` (case-insensitive) и `phone`.

---

## Тестирование

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

**Текущее покрытие:** 408 тестов, покрытие ~77%.

Ключевые модули с высоким покрытием:
- `app/core/scheduler.py` — 80%
- `app/core/state_machine.py` — 100%
- `app/llm/engine.py` — 99%
- `app/llm/guardrails.py` — 98%
- `app/services/notification_service.py` — 96%

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

### P1.3: Метрики засоряются для paused/closed кампаний

- **Риск:** Аналитика показывает «ответы» по неактивным (paused/closed) кампаниям.
- **Реальность:** Некрасиво, но не ломает функционал. Заказчик увидит цифры и подумает «странно», но продажи не пострадают.
- **Решение:** Перенести обновление `campaign.replied_count` и `CampaignContact.status = "replied"` после проверки `campaign.status == "running"` — 3 строки.

### P2: `processed_contacts` считает сообщения, а не уникальные контакты

Если 5 контактов получили initial + follow-up, в UI отобразится `10/10` вместо `5/10`. Семантически неверно, но не критично для работы.

### P2: `assigned_account_id` без проверки статуса

Если контакт закреплен за аккаунтом в `cooldown` или без `session_string`, система попытается использовать его и упадет в `except`. Контакт будет пропущен до следующего прогона. Fallback на другой аккаунт работает только при `assigned_account_id = null`.

---

## Roadmap

- [ ] Inbound rate limit & daily limit guard
- [ ] Redis distributed lock для `conversation_id`
- [ ] Ручной takeover диалога оператором (`is_paused_by_operator`)
- [ ] Funnel-аналитика по стадиям
- [ ] Учет `processed_contacts` по уникальным контактам, а не сообщениям
- [ ] Поддержка голосовых сообщений и фото
- [ ] Автоматическая интеграция с календарем (Google Calendar / Calendly) при `meeting_intent`
- [ ] A/B тестирование скриптов
- [ ] WebSocket real-time dashboard

Подробнее см. [`docs/roadmap.md`](docs/roadmap.md).

---

## Лицензия

Proprietary — Neural Lead Team
