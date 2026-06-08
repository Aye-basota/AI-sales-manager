# AI Sales Manager

AI Sales Manager — система автоматизации B2B outbound продаж через Telegram с использованием живых аккаунтов (MTProto) и LLM для human-like коммуникации.

## Архитектура

- **FastAPI** — REST API
- **PostgreSQL** — основная БД
- **Redis** — очереди и кэш
- **aiogram 3.x** — Admin Telegram Bot
- **Pyrogram** — MTProto клиент для user-аккаунтов
- **APScheduler** — планировщик кампаний
- **OpenRouter** — LLM API (Qwen / Gemini / DeepSeek)

## Запуск

```bash
cp .env.example .env
# отредактируй .env

docker-compose up -d
```

## Разработка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Структура проекта

```
ai-sales-manager/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Pydantic Settings
│   ├── api/                 # REST endpoints
│   ├── bots/                # Telegram интерфейсы
│   ├── core/                # Бизнес-логика
│   ├── llm/                 # LLM интеграции
│   ├── models/              # SQLAlchemy модели
│   ├── services/            # Сервисный слой
│   └── db/                  # Миграции и подключение
├── scripts/                 # Утилиты
└── tests/                   # Тесты
```

## Лицензия

Proprietary — Neural Lead Team
