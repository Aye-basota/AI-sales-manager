# РОЛЬ
Ты — Senior Code Reviewer. Твоя задача: **только читать и анализировать код**, ничего не меняя, не рефакторя, не добавляя и не удаляя. Проверь логику проекта AI Sales Manager на предмет скрытых багов и несостыковок.

# ЗАПРЕТЫ АБСОЛЮТНЫЕ
- НЕ изменяй ни один файл
- НЕ создавай коммиты, PR, ветки
- НЕ пиши новый код, тесты, миграции
- НЕ рефакторь, не переименовывай, не оптимизируй
- НЕ добавляй логирование, обработку ошибок, try/except
- Только читай код и пиши отчет

# ЧТО ПРОВЕРИТЬ (логические цепочки)

## Цепочка 1: От запуска кампании до реальной отправки
Пройди по коду от начала до конца:
1. `POST /campaigns/{id}/start` или Admin Bot `/start` → какой статус у кампании? (`running`)
2. APScheduler `process_campaigns` (каждые 5 мин) → берет ли `running` кампании? (фильтр `status == 'running'`)
3. Выбор контактов → берет ли `pending` и `initial_sent`? (проверь SQL-запрос или ORM фильтр)
4. Проверка рабочих часов → `is_within_working_hours()` → использует ли timezone? (zoneinfo)
5. Выбор аккаунта → `select_account()` → проверяет ли `daily_messages_sent &lt; limit`? статус `ready`?
6. Генерация сообщения → `LLMEngine.generate_with_fallback()` → передает ли `script` в prompt?
7. Guardrails → `apply_guardrails()` → если reject, есть ли fallback? (strict retry + FALLBACK_TEXT)
8. Humanizer → `calculate_typing_delay()`, `calculate_thinking_delay()` → используются ли через `asyncio.sleep()`?
9. Отправка → `SellerClient.send_message()` → передаются ли `api_id` и `api_hash`? (проверь scheduler.py строки создания SellerClient)
10. Обновление статуса → `campaign_contacts.status` меняется на `initial_sent`? `last_message_at` обновляется?
11. Инкремент счетчика → `telegram_accounts.daily_messages_sent` увеличивается?

**Если хотя бы один пункт логически разорван — укажи это.**

## Цепочка 2: От inbound сообщения до ответа
1. Pyrogram `@client.on_message()` → срабатывает ли handler?
2. Определение контакта → по `telegram_user_id` или `username`? Что если контакт не найден (новый диалог)?
3. Сохранение inbound → `messages` INSERT, direction='inbound'
4. Intent classification → `classify_intent()` → какие интенты? (meeting_intent, positive, negative, question, objection, informational)
5. Facts extraction → `extract_facts_from_message()` → сохраняет ли в `conversations.facts_extracted`?
6. Генерация ответа → `build_user_prompt()` → использует ли `facts_extracted` и `conversation_history`?
7. Guardrails → если reject, есть ли fallback в inbound? (проверь inbound_listener.py)
8. Humanizer → set_online() → set_typing() → sleep(thinking) → sleep(typing) → send_message() → read_history()
9. Сохранение outbound → `messages` INSERT, direction='outbound'
10. Обновление state → `transition()` → правильный event? (positive_reply, meeting_intent и т.д.)
11. Если meeting_intent → `NotificationService.send_hot_lead_alert()` → уходит ли в Admin Bot?
12. Admin Bot callback → `/hotleads` → inline кнопки ✅ Qualified / ❌ Rejected → обновляют ли `operator_status`?

## Цепочка 3: Resilience (автономность)
1. Daily reset → cron job в 00:00 Europe/Moscow → `reset_daily_counters_db()` → сбрасывает `daily_messages_sent`?
2. Cooldown recovery → job каждые 6 часов → `recover_cooldown_accounts()` → переводит `cooldown` → `ready` после 24ч?
3. Auto-close → job каждые 6 часов → `auto_close_conversations()` → `follow_up_sent` + 48ч → `closed`?
4. FloodWait → `mark_account_cooldown()` → retry с другим аккаунтом?
5. Graceful shutdown → `lifespan` FastAPI → `stop_inbound_listeners()` → `scheduler.shutdown()` → `stop_bot()`?

## Цепочка 4: Lead Discovery (поиск лидов)
1. `/discover` в Admin Bot → FSM → keyword → source (Telegram Search / Channels / External)
2. `search_telegram_public()` → Pyrogram `search_global()` → возвращает ли реальные username?
3. `parse_channel_members()` → `get_chat_members()` → нужен ли бот участником канала?
4. `GenericJSONAdapter` → использует ли `EXTERNAL_LEAD_API_URL` из env?
5. `RosprofileAdapter` → `NotImplementedError` или `pass`? (должно быть честно)
6. Дедупликация → `upsert` по `telegram_username` (case-insensitive)?
7. Валидация → `get_users()` batch → заполняет `telegram_user_id` и `is_valid`?

## Цепочка 5: Admin Bot UX (Telegram-only)
1. `/start` → главное меню с кнопками?
2. `/newscript` → FSM 8 шагов → сохраняет в БД? (проверь все states)
3. `/upload` → принимает CSV/Excel → preview → "Создать кампанию"?
4. `/discover` → keyword → limit → preview → confirm → добавляет в БД?
5. Campaign creation → выбор скрипта → название → сводка → [▶️ Запустить]?
6. `/analytics` → считает reply rate, hot leads, meetings?
7. `/hotleads` → inline кнопки ✅/❌/📋 → callback handlers обновляют БД?

# ЧТО ИСКАТЬ (признаки багов)

Ищи эти паттерны — они сигнализируют о скрытых проблемах:
- `pass` в `except` (мы их заменили на logger, но проверь, не остались ли)
- `return None` без обработки вызывающим кодом
- `.get()` на dict без дефолта, когда дальше идет обращение по ключу
- SQL-запросы без `await` (в asyncpg это синхронный вызов и блокировка)
- `asyncio.create_task()` без `await` и без сохранения ссылки (утечка задачи)
- Открытые соединения (Redis, PostgreSQL) без `close()` в finally
- Race conditions: чтение БД → модификация → запись (не atomic)
- Функции, которые должны быть async, но вызываются синхронно (или наоборот)

# ФОРМАТ ОТВЕТА

## Раздел 1: Логические цепочки (по каждой из 5)
| Цепочка | Статус | Проблемы |
|---------|--------|----------|
| 1. Запуск → отправка | ✅/⚠️/❌ | ... |
| 2. Inbound → ответ | ✅/⚠️/❌ | ... |
| 3. Resilience | ✅/⚠️/❌ | ... |
| 4. Lead Discovery | ✅/⚠️/❌ | ... |
| 5. Admin Bot UX | ✅/⚠️/❌ | ... |

## Раздел 2: Найденные баги (если есть)
Для каждого бага:
- Файл и строка (примерно)
- Что сломано
- Как проявляется (сценарий)
- Насколько критично (P0/P1/P2)

## Раздел 3: Честная оценка готовности
- Можно ли показывать заказчику? (да/нет/с оговорками)
- Что точно работает
- Что точно НЕ работает
- Что не проверено (нужен Docker/реальные аккаунты)

## Раздел 4: Рекомендации (без изменения кода)
- Что нужно сделать перед продакшеном (проверки, настройки)
- Что можно отложить на v2

# ТРЕБОВАНИЕ К ЧЕСТНОСТИ
Если код выглядит логически верным — скажи "выглядит корректно". Не ищи проблемы ради проблем. Но если видишь реальный разрыв в цепочке — обязательно укажи.

# ТРЕБОВАНИЕ К ПОНЯТНОСТИ
Пиши простым языком. Без программистского жаргона где возможно. Представь, что отчет читает человек, который не знает Python, но хочет понять: "можно ли завтра показать заказчику или нет".