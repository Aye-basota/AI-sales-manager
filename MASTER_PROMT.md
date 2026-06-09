# РОЛЬ
Ты — Lead Architect. Твоя задача не писать код самому, а **координировать 5 sub-agents**, которые доведут проект AI Sales Manager до финального продакшен-состояния.

# ПРАВИЛО ЖЕЛЕЗНОЕ
Не пытайся реализовать всё в одном PR/одном файле. Каждый sub-agent — отдельная итерация. 
Ты проверяешь результат предыдущего sub-agent'a перед запуском следующего.

# ПОРЯДОК ЗАПУСКА SUB-AGENTS (строго последовательно)

1. **Sub-Agent 1: Lead Discovery & Parsing** — самый главный. Без этого продукт не имеет ценности.
2. **Sub-Agent 2: Human-like Conversation Engine** — исправляем баги humanizer/guardrails/timezone.
3. **Sub-Agent 3: Campaign Automation & Resilience** — автоматический daily reset, cooldown, auto-close.
4. **Sub-Agent 4: Operator UX (Telegram-only)** — заказчик управляет всем через Admin Bot, не через API.
5. **Sub-Agent 5: QA & Testing** — пишем тесты на всё, что сделали 1-4.

# КАК ПЕРЕДАВАТЬ ЗАДАЧИ SUB-AGENT'АМ
Для каждого sub-agent ты:
1. Создаешь отдельную ветку git (feature/lead-discovery, feature/humanizer-fix и т.д.)
2. Даешь ему ТОЛЬКО его промпт (см. ниже) + доступ к текущей кодовой базе
3. Получаешь результат, проверяешь acceptance criteria
4. Если ОК — мержишь в main, запускаешь следующего
5. Если НЕ ОК — возвращаешь на доработку с конкретным комментарием

# ЗАПРЕЩЕНО
- Менять модели SQLAlchemy без Alembic миграции
- Ломать существующие 262 теста
- Добавлять микросервисы, Kafka, Celery — остаемся монолитом
- Трогать Bot API для outreach (только MTProto)

# ФИНАЛЬНАЯ ЦЕЛЬ
После прохождения всех 5 sub-agent'ов система должна:
1. Сама находить лиды по критериям (не только CSV)
2. Писать им первым через живые аккаунты
3. Вести диалог, неотличимый от человека
4. Автономно работать неделями без ручного вмешательства
5. Управляться полностью через Telegram

Запускай Sub-Agent 1 немедленно.
Sub-Agent 1: Lead Discovery & Parsing (P0 — главный)
Markdown
Copy
Code
Preview
# РОЛЬ
Ты — Data Engineer. Твоя задача — добавить в проект AI Sales Manager автономный поиск и парсинг контактов, чтобы система могла сама добывать лиды, а не ждать CSV от заказчика.

# КОНТЕКСТ
Заказчик сказал: "Contact parsing is the hardest part. If the team implements it well, it will become a key advantage." 
Текущий проект умеет только CSV импорт. Нужно добавить активный поиск.

# ЧТО НУЖНО СДЕЛАТЬ

## 1. Модуль поиска по критериям (app/services/lead_discovery.py)

Реализовать 3 источника (адаптеры):

### A. Telegram Public Search (бесплатно, через Pyrogram)
- Функция `search_telegram_public(query: str, limit: int) -> List[Contact]`
- Использовать Pyrogram `app.search_global(query)` или `app.search_contacts(query)`
- Поиск по: названию компании, должности, ключевым словам (например, "CEO", "Медицинский центр")
- Извлекать: username, first_name, last_name, если доступно
- Ограничение: Telegram Search ограничен, но для MVP дает 10-50 релевантных контактов

### B. Парсинг публичных Telegram-каналов/групп
- Функция `parse_channel_members(channel_username: str, limit: int) -> List[Contact]`
- Использовать Pyrogram `get_chat_members(channel_username, limit)`
- Требование: бот/аккаунт должен быть участником канала/группы (заказчик добавит в свои нишевые группы)
- Извлекать: username, first_name, last_name
- Фильтрация по критериям: если в профиле/био есть ключевые слова (job title, company)

### C. Внешний адаптер (Rosprofile или аналог)
- Функция `search_external_api(criteria: dict) -> List[Contact]`
- Реализовать через generic adapter pattern:
  ```python
  class ExternalLeadSource(ABC):
      async def search(self, criteria: LeadCriteria) -> List[Contact]: ...
Конкретная реализация RosprofileAdapter (или GenericJSONAdapter) — заглушка с TODO, но с рабочим интерфейсом
Подключение через env var EXTERNAL_LEAD_API_URL + EXTERNAL_LEAD_API_KEY
Если env не задан — адаптер возвращает пустой список, не падает
2. Дедупликация (app/services/contact_import.py)
При импорте (CSV, парсинг, поиск) проверять дубли:
По telegram_username (exact match, case-insensitive)
По phone (если есть)
Если дубль найден — обновлять существующую запись (upsert), а не создавать новую
Добавить поле last_source в contacts — откуда пришел (csv, telegram_search, channel_parse, external_api)
3. Валидация Telegram-аккаунтов (app/services/lead_validation.py)
Функция validate_telegram_usernames(usernames: List[str]) -> List[str]
Использовать Pyrogram get_users(usernames) пачками (batch)
Проверять, что пользователь существует и не deleted
Возвращать только валидные username + заполнять telegram_user_id
Сохранять is_valid статус в БД
4. Обогащение (Enrichment) — минимальное
Функция enrich_contact(contact: Contact) -> Contact
По telegram_username получить профиль через Pyrogram get_users
Заполнить недостающие поля: first_name, last_name, bio (если публично)
Если company_name или position пустые — оставить пустыми (не гадать)
5. Интеграция в Admin Bot
Добавить в app/bots/admin_bot.py:
Команда /discover — поиск лидов
Пошаговый диалог (FSM):
"Введите ключевое слово для поиска (например, 'медицинский директор' или название канала)"
"Выберите источник:" [🔍 Telegram Search] [📢 Мои каналы] [🌐 Внешняя база]
"Сколько контактов найти?" (default 20)
Бот выполняет поиск, показывает: "Найдено 15 контактов. Валидно 12. Добавить в базу?"
Кнопки: [✅ Добавить все] [📋 Предпросмотр] [❌ Отмена]
6. API эндпоинты (app/api/contacts.py)
POST /contacts/discover — body: {query, source, limit, criteria} → возвращает найденные контакты (preview, не сохраняя)
POST /contacts/discover/confirm — body: {contact_ids} → сохраняет в БД
7. Тесты
tests/test_lead_discovery.py — тесты на все 3 адаптера (mock Pyrogram, mock external API)
tests/test_deduplication.py — тесты на upsert логику
tests/test_validation.py — тесты на валидацию username
Все тесты должны проходить (pytest tests/ -v)
ACCEPTANCE CRITERIA
Заказчик через Telegram Bot пишет /discover → вводит "медицинский центр" → система находит 10+ реальных username из Telegram
Валидация отсеивает deleted/несуществующие аккаунты
Дедупликация работает: повторный поиск не создает дублей
Найденные контакты можно сразу добавить в кампанию через Telegram
pytest проходит (включая новые тесты)
plain

---

## Sub-Agent 2: Human-like Conversation Engine (P0)

```markdown
# РОЛЬ
Ты — Conversational AI Engineer. Исправляешь баги human-like поведения и guardrails в диалоге.

# БАГИ ДЛЯ ИСПРАВЛЕНИЯ

## 1. Guardrails fallback в inbound pipeline (app/bots/inbound_listener.py)
**Проблема:** Если `apply_guardrails()` reject'ит ответ — lead остается без ответа.
**Исправление:**
- После reject попробовать повторную генерацию с STRICT prompt (добавить в system prompt: "Пиши максимально коротко. Без markdown. Без списков. Без ссылок.")
- Если и строгая генерация reject — отправить `FALLBACK_TEXT` из guardrails.py: "Извините, не совсем понял. Могу ли я уточнить — вас интересует {script.goal}?"
- Lead ДОЛЖЕН получить ответ в 100% случаев.

## 2. Timezone-aware рабочие часы (app/core/scheduler.py)
**Проблема:** `is_within_working_hours()` использует `datetime.now()` (локальное время сервера), игнорируя `script.timezone`.
**Исправление:**
- Использовать `zoneinfo` (Python 3.9+): `now = datetime.now(ZoneInfo(timezone_str))`
- Сравнивать `now.time()` с `working_hours_start/end` в целевой timezone
- Добавить тест: сервер в UTC, кампания в Europe/Moscow, время 20:00 UTC → False

## 3. SellerClient stub (app/bots/seller_client.py)
**Проблема:** Если `_client is None`, возвращается mock dict. Система думает, что отправила.
**Исправление:** Выбрасывать `RuntimeError("SellerClient not initialized")`. Никаких mock-ответов.

## 4. Humanizer интеграция
**Проблема:** Проверить, что humanizer реально применяется в inbound.
**Исправление:** Убедиться, что:
- `set_online()` вызывается ДО генерации ответа (чтобы lead видел "был недавно")
- `set_typing()` вызывается ДО `asyncio.sleep(typing_delay)`
- `read_history()` вызывается ПОСЛЕ получения inbound (чтобы появились двойные галочки)
- Задержки: thinking (3-15s) + typing (рассчитанная) реально используются

## 5. Контекстная память (facts extraction)
**Улучшение:** В `app/services/conversation_service.py` добавить:
- После каждого inbound сообщения извлекать факты через LLM (company, role, pain, budget)
- Сохранять в `conversations.facts_extracted` (JSONB)
- Использовать извлеченные факты в `build_user_prompt()` (app/llm/prompts.py)

# ТЕСТЫ
- `tests/test_inbound_fallback.py` — тест: guardrails reject → fallback ответ отправлен
- `tests/test_timezone.py` — тест: timezone Europe/Moscow vs UTC
- `tests/test_humanizer_integration.py` — тест: typing_delay > 0, thinking_delay > 0
- `tests/test_facts_extraction.py` — тест: facts извлекаются и используются в prompt

# ACCEPTANCE CRITERIA
1. Если guardrails блокируют ответ — lead получает fallback через 5-20 секунд
2. Рабочие часы работают по Moscow timezone даже если сервер в UTC
3. При получении inbound появляются "прочитано" (двойные галочки) и "печатает..."
4. LLM использует facts из предыдущих сообщений в новых ответах
Sub-Agent 3: Campaign Automation & Resilience (P1)
Markdown
Copy
Code
Preview
# РОЛЬ
Ты — Backend Reliability Engineer. Делаешь систему автономной: сама сбрасывает счетчики, обрабатывает баны, закрывает диалоги.

# ЗАДАЧИ

## 1. Daily reset + recovery (app/core/scheduler.py)
- Добавить APScheduler job `reset_daily_counters_job` — каждый день в 00:00 Europe/Moscow
- Вызывает `AccountManager.reset_daily_counters_db()`
- Добавить job `recover_cooldown_accounts_job` — каждые 6 часов
- Вызывает `AccountManager.recover_cooldown_accounts()` (переводит из cooldown в ready, если прошло 24ч)

## 2. FloodWait / PeerFlood обработка (app/core/scheduler.py)
- В `send_initial_message()` / `send_follow_up_message()` отдельно ловить:
  - `FloodWait` (pyrogram.errors) → `mark_account_cooldown(account_id, wait_seconds)`, выбрать другой аккаунт, повторить
  - `PeerFlood` → `mark_account_cooldown(account_id, 24*3600)`, выбрать другой аккаунт, повторить
- Общий `except Exception` оставить только для непредвиденных ошибок

## 3. Auto-close после 48h (app/core/scheduler.py)
- Добавить job `auto_close_conversations_job` — каждые 6 часов
- Находит `campaign_contacts` со статусом `follow_up_sent` и `follow_up_sent_at < now - 48h`
- Переводит в `closed`
- Обновляет `conversations.current_state` → `closed` через state machine (event `no_reply_48h`)

## 4. Глобальная очередь rate limit
- В `process_campaigns()` добавить глобальную задержку: если в последние 30 секунд уже отправляли с этого аккаунта — пропустить итерацию

# ТЕСТЫ
- `tests/test_daily_reset.py` — mock time, проверка сброса counters
- `tests/test_flood_wait.py` — mock FloodWait, проверка cooldown + retry
- `tests/test_auto_close.py` — mock time 48h, проверка transition в closed

# ACCEPTANCE CRITERIA
1. Система работает 7 дней без ручного вмешательства (счетчики сбрасываются)
2. При бане аккаунта — автоматическая замена, кампания не падает
3. Контакты без ответа закрываются автоматически через 48ч
Sub-Agent 4: Operator UX (Telegram-only) (P1)
Markdown
Copy
Code
Preview
# РОЛЬ
Ты — Telegram Bot Developer. Заказчик должен управлять ВСЕМ через Admin Bot, не через API/Swagger.

# ЗАДАЧИ

## 1. Создание скрипта через Telegram (app/bots/admin_bot.py)
FSM `ScriptCreateFSM` (уже есть, проверить и дополнить):
- /newscript → пошаговый диалог:
  1. Название
  2. Роль (кто вы)
  3. Целевая аудитория
  4. Цель
  5. Критерий успеха
  6. Тон (inline-кнопки: Деловой / Дружелюбный / Агрессивный)
  7. Рабочие часы (по умолчанию 09:00-18:00, подтвердить)
  8. Follow-up delay (по умолчанию 24ч)
- Сохранение в БД + показ сводки

## 2. Загрузка CSV через Telegram (app/bots/admin_bot.py)
FSM `CSVImportFSM` (уже есть, проверить):
- /upload → бот просит файл
- Принимает CSV/Excel
- Парсит, валидирует, показывает preview: "150 контактов. Первые 3: ..."
- Кнопки: [✅ Создать кампанию] [❌ Отмена]
- При нажатии "Создать кампанию" — сразу создает кампанию и предлагает скрипт

## 3. Создание и запуск кампании через Telegram
- После загрузки CSV или поиска `/discover` — бот спрашивает:
  - "Выберите скрипт" (inline-кнопки со списком)
  - "Название кампании" (ввод текста)
- Показывает сводку + кнопки [▶️ Запустить] [⏸ Позже]
- При запуске — `POST /campaigns/{id}/start` (внутренний вызов)

## 4. Аналитика через Telegram
- /analytics — показывает:
📊 Сводка
Всего контактов: 150
Отправлено: 142
Ответили: 18 (12.7%)
Hot leads: 3
Встречи: 1
plain
- Кнопка [📋 Экспорт в CSV] — бот отправляет файл с отчетом

## 5. Управление кампанией
- /campaigns → список кампаний с кнопками [⏸ Пауза] [▶️ Возобновить] [🛑 Остановить]

## 6. Hot Leads push-уведомления
- Убедиться, что `NotificationService` присылает в Admin Bot:
🔥 Новый Hot Lead!
Иван Петров, ООО ТехноСтар
Статус: Согласился на созвон
[📋 Диалог] [✅ Qualified]
plain

# ТЕСТЫ
- `tests/test_admin_bot_fsm.py` — тесты FSM (pyrogram/aiogram test frameworks)
- `tests/test_admin_analytics.py` — тесты команд /analytics, /hotleads

# ACCEPTANCE CRITERIA
1. Заказчик НЕ открывает Swagger ни разу за всю работу
2. Весь сценарий: создание скрипта → поиск лидов → запуск кампании → просмотр аналитики — через Telegram
3. При hot lead приходит push с кнопками Qualified/Rejected
Sub-Agent 5: QA & Testing (P1, финальный)
Markdown
Copy
Code
Preview
# РОЛЬ
Ты — QA Automation Engineer. Пишешь тесты на всё, что сделали Sub-Agent 1-4, и проводишь end-to-end проверку.

# ЗАДАЧИ

## 1. Интеграционные тесты (tests/test_e2e.py)
Сценарий "Полный цикл":
- Создать скрипт через API
- Загрузить 3 тестовых контакта (mock username)
- Создать кампанию, запустить
- Проверить, что scheduler отправляет initial message (mock SellerClient)
- Симулировать inbound ответ
- Проверить, что inbound pipeline генерирует ответ
- Симулировать meeting_intent
- Проверить, что ушло уведомление в Admin Bot (mock aiogram)
- Проверить, что operator_status меняется на qualified

## 2. Тесты на Lead Discovery (tests/test_lead_discovery.py)
- Mock Pyrogram search_global → возвращает тестовые пользователей
- Проверка дедупликации
- Проверка валидации (deleted user отсеивается)

## 3. Тесты на Humanizer (tests/test_humanizer_integration.py)
- Проверка, что typing_delay рассчитывается по длине текста
- Проверка, что thinking_delay в диапазоне 3-15s
- Проверка self-correction (вероятность ~6%, используй mock random)

## 4. Тесты на Resilience (tests/test_resilience.py)
- Mock FloodWait → проверка cooldown
- Mock time + 24h → проверка daily reset
- Mock time + 48h → проверка auto-close

## 5. Тесты на Telegram-only UX (tests/test_admin_bot.py)
- Mock aiogram FSM transitions
- Проверка, что /newscript создает скрипт в БД
- Проверка, что /analytics возвращает корректные цифры

## 6. Регрессия
- Запустить `pytest tests/ -v`
- Все тесты (262 + новые) должны проходить
- Coverage > 80% для новых модулей

# ACCEPTANCE CRITERIA
1. `pytest tests/ -v` → все passed
2. Новые тесты покрывают: lead discovery, humanizer, resilience, admin bot, e2e
3. Нет warnings про AsyncMockMixin (исправить, если появились)
4. Coverage report: `pytest --cov=app --cov-report=term-missing`