from __future__ import annotations

from typing import Any

from app.core.funnel import (
    get_stage_config,
    get_max_length_for_stage,
    is_call_to_action_allowed,
)

DEFAULT_INTENT_LABELS = [
    "meeting_intent",
    "question",
    "objection",
    "positive",
    "negative",
    "informational",
]


def _language_rule(language: str) -> str:
    if language.lower() == "ru":
        return "Пиши только на русском языке. Не добавляй переводы на другие языки."
    if language.lower() == "en":
        return "Write only in English. Do not add translations to other languages."
    return f"Пиши только на языке: {language}. Не добавляй переводы на другие языки."


def _emoji_rule(policy: str) -> str:
    if policy == "forbidden":
        return "Не используй эмодзи."
    if policy == "rare":
        return "Используй эмодзи очень редко, только если это уместно."
    return "Эмодзи разрешены, но используй их умеренно."


def build_system_prompt(
    script: Any,
    conversation_stage: str = "hook",
    company_name: str = "Neural Lead",
) -> str:
    """Build a dynamic system prompt based on the script and funnel stage.

    The prompt is split into:
    - global persona and rules (always present);
    - stage-specific instructions (hook/qualification/value/cta).
    """
    role = script.role_prompt or "Ты менеджер по продажам."
    audience = script.target_audience or ""
    goal = script.goal or "Довести до созвона."
    criteria = script.success_criteria or "Клиент согласился на демо или назвал удобное время."
    tone = script.tone or "professional"
    language = getattr(script, "language", None) or "ru"
    emoji_policy = getattr(script, "emoji_policy", None) or "forbidden"

    audience_line = f"\nЦелевая аудитория: {audience}" if audience else ""

    stage_cfg = get_stage_config(script, conversation_stage)
    stage_goal = stage_cfg.get("goal", goal)
    stage_instructions = stage_cfg.get(
        "instructions",
        "Напиши короткое, естественное сообщение.",
    )
    max_length = get_max_length_for_stage(script, conversation_stage)
    cta_allowed = is_call_to_action_allowed(script, conversation_stage)
    cta_text = getattr(script, "call_to_action", None) or "15-минутный созвон"

    cta_rule = (
        f"Призыв к действию: можешь предложить {cta_text} и 2 варианта времени."
        if cta_allowed
        else "Запрещено предлагать созвон/встречу на этом этапе."
    )

    return (
        f"Ты — менеджер по продажам {company_name}. Ты пишешь из личного Telegram "
        f"аккаунта потенциальному клиенту.\n\n"
        f"РОЛЬ:\n{role}{audience_line}\n\n"
        f"ЦЕЛЬ ДИАЛОГА:\n{goal}\n\n"
        f"КРИТЕРИЙ УСПЕХА:\n{criteria}\n\n"
        f"ТОНАЛЬНОСТЬ: {tone}\n\n"
        f"ТЕКУЩИЙ ЭТАП ВОРОНКИ: {conversation_stage}\n"
        f"Цель этапа: {stage_goal}\n\n"
        f"ПРАВИЛА ГЕНЕРАЦИИ:\n"
        f"1. Пиши как живой человек: короткие абзацы, разговорный тон.\n"
        f"2. Пиши от первого лица как сотрудник компании.\n"
        f"3. {_language_rule(language)}\n"
        f"4. {_emoji_rule(emoji_policy)}\n"
        f"5. Разделяй текст на 1-3 коротких абзаца по смыслу. "
        f"Не отправляй всё одним сплошным полотном.\n"
        f"6. Никогда не используй markdown, списки, жирный шрифт. Пиши plain text.\n"
        f"7. Никогда не признавайся что ты бот или ИИ. Не упоминай автоматизированные сервисы.\n"
        f"8. Не добавляй P.S., примечания и уточнения в скобках.\n"
        f"9. Максимальная длина сообщения: {max_length} символов.\n"
        f"10. {cta_rule}\n"
        f"11. При возражениях — не дави, используй техники:\n"
        f"   - Цена: \"Многие так думают, но когда посчитали ROI...\"\n"
        f"   - Не нужно: \"Понимаю, а как сейчас решаете эту задачу?\"\n"
        f"   - Позже: \"Конечно, а когда планируете?\"\n\n"
        f"ИНСТРУКЦИЯ К ТЕКУЩЕМУ ЭТАПУ ({conversation_stage}):\n"
        f"{stage_instructions}"
    )


def _build_facts_block(lead_facts: dict[str, Any]) -> str:
    if not lead_facts:
        return "(нет данных)"
    lines = []
    for key, value in lead_facts.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _build_history_block(conversation_history: list[dict[str, Any]]) -> str:
    if not conversation_history:
        return "(пусто)"
    lines = []
    for msg in conversation_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def build_user_prompt(
    conversation_history: list[dict],
    lead_facts: dict,
    last_agent_message: str,
    lead_message: str,
) -> str:
    """Generic user prompt (kept for backward compatibility)."""
    history_block = _build_history_block(conversation_history)
    facts_block = _build_facts_block(lead_facts)

    return (
        f"КОНТЕКСТ ДИАЛОГА:\n{history_block}\n\n"
        f"ФАКТЫ О ЛИДЕ:\n{facts_block}\n\n"
        f"ТВОЯ ПРЕДЫДУЩАЯ РЕПЛИКА:\n{last_agent_message}\n\n"
        f"ОТВЕТ КЛИЕНТА:\n{lead_message}\n\n"
        f"Напиши ответ (1-3 коротких абзаца). Не используй приветствия, "
        f"если это не первое сообщение."
    )


def build_initial_user_prompt(
    script: Any,
    contact: Any,
    conversation_stage: str = "hook",
) -> str:
    """Build the user prompt for the first outbound message."""
    stage_cfg = get_stage_config(script, conversation_stage)
    stage_instructions = stage_cfg.get(
        "instructions",
        "Напиши короткое первое сообщение для потенциального клиента.",
    )
    max_length = get_max_length_for_stage(script, conversation_stage)

    facts: dict[str, Any] = {}
    if contact:
        for attr in ("first_name", "company_name", "position", "city", "industry"):
            value = getattr(contact, attr, None)
            if value:
                facts[attr] = value

    facts_block = _build_facts_block(facts)

    return (
        f"Это ПЕРВОЕ сообщение потенциальному клиенту.\n"
        f"Текущий этап воронки: {conversation_stage}\n"
        f"Максимальная длина: {max_length} символов.\n\n"
        f"ИНСТРУКЦИЯ:\n{stage_instructions}\n\n"
        f"ФАКТЫ О КОНТАКТЕ:\n{facts_block}\n\n"
        f"Напиши первое сообщение. Не предлагай созвон. "
        f"Сообщение должно быть коротким и естественным."
    )


def build_reply_user_prompt(
    script: Any,
    conversation_history: list[dict],
    lead_facts: dict,
    last_agent_message: str,
    lead_message: str,
    conversation_stage: str = "hook",
) -> str:
    """Build the user prompt for replying to a lead message."""
    stage_cfg = get_stage_config(script, conversation_stage)
    stage_goal = stage_cfg.get("goal", "Дать короткий, естественный ответ клиенту.")
    max_length = get_max_length_for_stage(script, conversation_stage)
    cta_allowed = is_call_to_action_allowed(script, conversation_stage)
    cta_text = getattr(script, "call_to_action", None) or "15-минутный созвон"

    cta_note = (
        f"На этом этапе можно предложить {cta_text}."
        if cta_allowed
        else "На этом этапе НЕЛЬЗЯ предлагать созвон/встречу."
    )

    history_block = _build_history_block(conversation_history)
    facts_block = _build_facts_block(lead_facts)

    return (
        f"ВАЖНО: Это ОТВЕТ клиенту, а не первое сообщение. "
        f"Клиент уже получил первое сообщение и ответил на него. "
        f"Не повторяй первое сообщение — отвечай на его реплику.\n\n"
        f"Текущий этап воронки: {conversation_stage}\n"
        f"Цель этапа при ответе: {stage_goal}\n"
        f"Максимальная длина: {max_length} символов.\n"
        f"{cta_note}\n\n"
        f"КОНТЕКСТ ДИАЛОГА:\n{history_block}\n\n"
        f"ФАКТЫ О ЛИДЕ:\n{facts_block}\n\n"
        f"ТВОЯ ПРЕДЫДУЩАЯ РЕПЛИКА:\n{last_agent_message}\n\n"
        f"ОТВЕТ КЛИЕНТА:\n{lead_message}\n\n"
        f"Напиши ответ (1-3 коротких абзаца). Не используй приветствия."
    )


def build_follow_up_user_prompt(
    script: Any,
    conversation_history: list[dict],
    lead_facts: dict,
    last_agent_message: str,
    conversation_stage: str = "hook",
) -> str:
    """Build the user prompt for a follow-up message when the lead has not replied."""
    stage_cfg = get_stage_config(script, conversation_stage)
    stage_instructions = stage_cfg.get(
        "instructions",
        "Напиши короткое напоминание клиенту.",
    )
    max_length = get_max_length_for_stage(script, conversation_stage)
    cta_allowed = is_call_to_action_allowed(script, conversation_stage)
    cta_text = getattr(script, "call_to_action", None) or "15-минутный созвон"

    cta_note = (
        f"На этом этапе можно предложить {cta_text}."
        if cta_allowed
        else "На этом этапе НЕЛЬЗЯ предлагать созвон/встрепу."
    )

    history_block = _build_history_block(conversation_history)
    facts_block = _build_facts_block(lead_facts)

    return (
        f"Текущий этап воронки: {conversation_stage}\n"
        f"Максимальная длина: {max_length} символов.\n"
        f"{cta_note}\n\n"
        f"ИНСТРУКЦИЯ К ЭТАПУ:\n{stage_instructions}\n\n"
        f"КОНТЕКСТ ДИАЛОГА:\n{history_block}\n\n"
        f"ФАКТЫ О ЛИДЕ:\n{facts_block}\n\n"
        f"ТВОЯ ПРЕДЫДУЩАЯ РЕПЛИКА:\n{last_agent_message}\n\n"
        f"Клиент пока не ответил. Напиши мягкое follow-up сообщение (1-2 абзаца). "
        f"Не дави, сохраняй живой тон."
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
