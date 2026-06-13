from app.models.script import Script


DEFAULT_INTENT_LABELS = [
    "meeting_intent",
    "question",
    "objection",
    "positive",
    "negative",
    "informational",
]


def build_system_prompt(script: Script, company_name: str = "Neural Lead") -> str:
    role = script.role_prompt or "Ты менеджер по продажам."
    audience = script.target_audience or ""
    goal = script.goal or "Довести до созвона."
    criteria = script.success_criteria or "Клиент согласился на демо или назвал удобное время."
    tone = script.tone or "professional"

    audience_line = f"\nЦелевая аудитория: {audience}" if audience else ""

    return (
        f"Ты — менеджер по продажам {company_name}. Ты пишешь из личного Telegram "
        f"аккаунта потенциальному клиенту в первый раз.\n\n"
        f"РОЛЬ:\n{role}{audience_line}\n\n"
        f"ЦЕЛЬ ДИАЛОГА:\n{goal}\n\n"
        f"КРИТЕРИЙ УСПЕХА:\n{criteria}\n\n"
        f"ТОНАЛЬНОСТЬ: {tone}\n\n"
        f"ПРАВИЛА ГЕНЕРАЦИИ:\n"
        f"1. Пиши как живой человек: короткие абзацы, разговорный тон, "
        f"не используй markdown, списки, жирный шрифт и эмодзи.\n"
        f"2. Пиши от первого лица как сотрудник компании.\n"
        f"3. Пиши только на русском языке. Не добавляй переводы на другие языки, "
        f"не используй иероглифы, арабскую вязь или латиницу, кроме имён собственных "
        f"и общепринятых аббревиатур.\n"
        f"4. Разделяй текст на 1-3 коротких абзаца по смыслу. "
        f"Не отправляй всё одним сплошным полотном.\n"
        f"5. Если спрашивают что-то вне скрипта — ответь естественно, "
        f"но верни разговор к цели (созвон/демо).\n"
        f"6. При возражениях — не дави, используй техники:\n"
        f"   - Цена: \"Многие так думают, но когда посчитали ROI...\"\n"
        f"   - Не нужно: \"Понимаю, а как сейчас решаете эту задачу?\"\n"
        f"   - Позже: \"Конечно, а когда планируете?\"\n"
        f"7. Цель: получить согласие на 15-минутный звонок.\n"
        f"8. Если клиент согласен — предложи 2 варианта времени "
        f"(завтра или послезавтра, 11:00 или 16:00).\n"
        f"9. Не используй markdown, списки, жирный шрифт. Пиши plain text.\n"
        f"10. Не упоминай автоматизированные сервисы или технические системы.\n"
        f"11. Не добавляй P.S., примечания и уточнения в скобках.\n"
    )


def build_user_prompt(
    conversation_history: list[dict],
    lead_facts: dict,
    last_agent_message: str,
    lead_message: str,
) -> str:
    history_lines = []
    for msg in conversation_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        history_lines.append(f"{role}: {content}")
    history_block = "\n".join(history_lines) if history_lines else "(пусто)"

    facts_lines = []
    for key, value in lead_facts.items():
        facts_lines.append(f"- {key}: {value}")
    facts_block = "\n".join(facts_lines) if facts_lines else "(нет данных)"

    return (
        f"КОНТЕКСТ ДИАЛОГА:\n{history_block}\n\n"
        f"ФАКТЫ О ЛИДЕ:\n{facts_block}\n\n"
        f"ТВОЯ ПРЕДЫДУЩАЯ РЕПЛИКА:\n{last_agent_message}\n\n"
        f"ОТВЕТ КЛИЕНТА:\n{lead_message}\n\n"
        f"Напиши ответ (1-3 коротких абзаца). Не используй приветствия, "
        f"если это не первое сообщение."
    )


def build_intent_classification_prompt(message: str) -> str:
    examples = [
        ("Давайте созвонимся завтра в 11", "meeting_intent"),
        ("А сколько это стоит?", "question"),
        ("Нам это пока не нужно", "objection"),
        ("Интересно, расскажите подробнее", "positive"),
        ("Не пишите мне больше", "negative"),
        ("Я работаю в компании ООО Ромашка", "informational"),
    ]

    lines = [
        "Ты — классификатор намерений в B2B-переписке.",
        "Определи намерение лида по его сообщению.",
        "Верни ТОЛЬКО одну метку из списка, без пояснений.",
        "",
        "Доступные метки:",
    ]
    for label in DEFAULT_INTENT_LABELS:
        lines.append(f"- {label}")
    lines.append("")
    lines.append("Примеры:")
    for ex_msg, ex_label in examples:
        lines.append(f'Сообщение: "{ex_msg}"')
        lines.append(f"Метка: {ex_label}")
        lines.append("")
    lines.append(f'Сообщение: "{message}"')
    lines.append("Метка:")

    return "\n".join(lines)
