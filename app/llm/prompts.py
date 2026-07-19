from __future__ import annotations

from typing import Any

from app.config.prompts import load_prompt_config
from app.core.funnel import (
    get_stage_config,
    get_max_length_for_stage,
    is_call_to_action_allowed,
)
from app.llm.context import (
    build_verified_context_block,
    extract_offer_summary,
    sanitize_context_text,
    script_display_name,
)

DEFAULT_INTENT_LABELS = [
    "meeting_intent",
    "question",
    "objection",
    "positive",
    "negative",
    "informational",
]

_FACT_LABELS = {
    "first_name": "имя",
    "last_name": "фамилия",
    "company_name": "компания",
    "position": "должность",
    "city": "город",
    "industry": "сфера",
    "source_summary": "почему контакт релевантен",
    "source_message_text": "публичный контекст",
    "company": "компания",
    "role": "роль",
    "pain": "потребность",
    "budget": "бюджет",
}


def _prompt_config() -> dict[str, Any]:
    """Return the cached prompt configuration."""
    return load_prompt_config()


def _language_rule(language: str) -> str:
    rules = _prompt_config().get("language_rules", {})
    if language.lower() == "ru":
        return rules.get("ru", "Пиши только на русском языке.")
    if language.lower() == "en":
        return rules.get("en", "Write only in English.")
    return rules.get("default", "Пиши только на языке: {language}.").format(language=language)


def _emoji_rule(policy: str) -> str:
    rules = _prompt_config().get("emoji_rules", {})
    if policy == "forbidden":
        return rules.get("forbidden", "Не используй эмодзи.")
    if policy == "rare":
        return rules.get("rare", "Используй эмодзи очень редко.")
    return rules.get("default", "Эмодзи разрешены умеренно.")


def _format_template(template: str, **kwargs: Any) -> str:
    """Format a template, keeping unknown placeholders as-is."""
    # Use safe formatting so missing keys don't crash the app.
    class SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    return template.format_map(SafeDict(kwargs))


def build_system_prompt(
    script: Any,
    conversation_stage: str = "hook",
    company_name: str | None = None,
) -> str:
    """Build a dynamic system prompt based on the script, funnel stage, and prompt config."""
    cfg = _prompt_config()
    role = f"Оффер: {extract_offer_summary(script)}"
    audience = sanitize_context_text(getattr(script, "target_audience", "") or "")
    goal = (
        sanitize_context_text(getattr(script, "goal", "") or "")
        or "Довести до следующего уместного шага."
    )
    criteria = (
        sanitize_context_text(getattr(script, "success_criteria", "") or "")
        or "Клиент явно согласился на следующий шаг или задал предметный вопрос."
    )
    details = getattr(script, "business_details", None)
    details = details if isinstance(details, dict) else {}
    custom_tone = sanitize_context_text(details.get("custom_tone", ""), max_chars=300)
    tone = sanitize_context_text(getattr(script, "tone", "") or "") or "professional"
    if tone == "custom" and custom_tone:
        tone = f"свой стиль владельца: {custom_tone}"
    language = getattr(script, "language", None) or "ru"
    emoji_policy = getattr(script, "emoji_policy", None) or "forbidden"

    audience_line = f"\nЦелевая аудитория: {audience}" if audience else ""
    verified_context = build_verified_context_block(script)

    stage_cfg = get_stage_config(script, conversation_stage)
    stage_goal = sanitize_context_text(stage_cfg.get("goal", "") or goal)
    stage_instructions = stage_cfg.get(
        "instructions",
        "Напиши короткое, естественное сообщение.",
    )
    stage_instructions = sanitize_context_text(stage_instructions, max_chars=700)
    max_length = get_max_length_for_stage(script, conversation_stage)
    cta_allowed = is_call_to_action_allowed(script, conversation_stage)
    cta_text = (
        sanitize_context_text(getattr(script, "call_to_action", None) or "")
        or "15-минутный созвон"
    )

    cta_rule = (
        f"Призыв к действию: если интерес уже есть, можешь мягко предложить {cta_text}. "
        "Не навязывай время без согласия клиента."
        if cta_allowed
        else "Запрещено предлагать созвон/встречу на этом этапе."
    )

    nurturing_rules = cfg.get("nurturing_rules", "")

    template = cfg.get("system_prompt_template", "")
    return _format_template(
        template,
        company_name=script_display_name(script, company_name),
        role=role,
        audience_line=audience_line,
        verified_context=verified_context,
        goal=goal,
        criteria=criteria,
        tone=tone,
        language_rule=_language_rule(language),
        emoji_rule=_emoji_rule(emoji_policy),
        conversation_stage=conversation_stage,
        stage_goal=stage_goal,
        stage_instructions=stage_instructions,
        max_length=max_length,
        cta_rule=cta_rule,
        nurturing_rules=nurturing_rules,
    )


def _build_facts_block(lead_facts: dict[str, Any]) -> str:
    if not lead_facts:
        return "(нет данных)"
    lines = []
    for key, value in lead_facts.items():
        safe_key = sanitize_context_text(
            _FACT_LABELS.get(str(key), str(key)),
            max_chars=80,
        )
        safe_value = sanitize_context_text(value, max_chars=220)
        if safe_key and safe_value:
            lines.append(f"- {safe_key}: {safe_value}")
    if not lines:
        return "(нет данных)"
    return "\n".join(lines)


def _build_history_block(conversation_history: list[dict[str, Any]]) -> str:
    if not conversation_history:
        return "(пусто)"
    lines = []
    for msg in conversation_history[-10:]:
        role = msg.get("role", "")
        content = sanitize_context_text(msg.get("content", ""), max_chars=600)
        if not content:
            continue
        label = "Менеджер" if role in ("agent", "assistant", "outbound") else "Клиент"
        lines.append(f"{label}: {content}")
    if not lines:
        return "(пусто)"
    return "\n".join(lines)


def build_chat_history_messages(
    conversation_history: list[dict[str, Any]],
    *,
    limit: int = 10,
    max_chars_per_message: int = 800,
) -> list[dict[str, str]]:
    """Return recent dialogue as real chat messages for the LLM API."""
    messages: list[dict[str, str]] = []
    if not conversation_history:
        return messages

    for msg in conversation_history[-limit:]:
        raw_role = msg.get("role", "")
        content = sanitize_context_text(
            msg.get("content", ""),
            max_chars=max_chars_per_message,
        )
        if not content:
            continue
        role = "assistant" if raw_role in ("agent", "assistant", "outbound") else "user"
        messages.append({"role": role, "content": content})
    return messages


def build_user_prompt(
    conversation_history: list[dict],
    lead_facts: dict,
    last_agent_message: str,
    lead_message: str,
) -> str:
    """Generic user prompt (kept for backward compatibility)."""
    history_block = _build_history_block(conversation_history)
    facts_block = _build_facts_block(lead_facts)
    template = (
        "КОНТЕКСТ ДИАЛОГА:\n{history_block}\n\n"
        "ФАКТЫ О ЛИДЕ:\n{facts_block}\n\n"
        "ТВОЯ ПРЕДЫДУЩАЯ РЕПЛИКА:\n{last_agent_message}\n\n"
        "ОТВЕТ КЛИЕНТА:\n{lead_message}\n\n"
        "Напиши естественный короткий ответ, обычно одним абзацем."
    )

    return _format_template(
        template,
        history_block=history_block,
        facts_block=facts_block,
        last_agent_message=sanitize_context_text(last_agent_message, max_chars=600),
        lead_message=sanitize_context_text(lead_message, max_chars=600),
    )


def build_initial_user_prompt(
    script: Any,
    contact: Any,
    conversation_stage: str = "hook",
) -> str:
    """Build the user prompt for the first outbound message."""
    cfg = _prompt_config()
    stage_cfg = get_stage_config(script, conversation_stage)
    stage_instructions = stage_cfg.get(
        "instructions",
        "Напиши короткое первое сообщение для потенциального клиента.",
    )
    stage_instructions = sanitize_context_text(stage_instructions, max_chars=700)
    max_length = get_max_length_for_stage(script, conversation_stage)

    facts: dict[str, Any] = {}
    if contact:
        for attr in (
            "first_name",
            "company_name",
            "position",
            "city",
            "industry",
            "source_summary",
            "source_message_text",
        ):
            value = getattr(contact, attr, None)
            if value:
                facts[attr] = value

    facts_block = _build_facts_block(facts)

    template = cfg.get("user_prompts", {}).get("initial", "")
    return _format_template(
        template,
        conversation_stage=conversation_stage,
        max_length=max_length,
        stage_instructions=stage_instructions,
        facts_block=facts_block,
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
    cfg = _prompt_config()
    stage_cfg = get_stage_config(script, conversation_stage)
    stage_goal = sanitize_context_text(
        stage_cfg.get("goal", "") or "Дать короткий, естественный ответ клиенту."
    )
    max_length = get_max_length_for_stage(script, conversation_stage)
    cta_allowed = is_call_to_action_allowed(script, conversation_stage)
    cta_text = (
        sanitize_context_text(getattr(script, "call_to_action", None) or "")
        or "15-минутный созвон"
    )

    cta_note = (
        f"На этом этапе можно предложить {cta_text}."
        if cta_allowed
        else "На этом этапе НЕЛЬЗЯ предлагать созвон/встречу."
    )

    history_block = _build_history_block(conversation_history)
    facts_block = _build_facts_block(lead_facts)

    template = cfg.get("user_prompts", {}).get("reply", "")
    return _format_template(
        template,
        conversation_stage=conversation_stage,
        stage_goal=stage_goal,
        max_length=max_length,
        cta_note=cta_note,
        history_block=history_block,
        facts_block=facts_block,
        last_agent_message=sanitize_context_text(last_agent_message, max_chars=600),
        lead_message=sanitize_context_text(lead_message, max_chars=600),
    )


def build_follow_up_user_prompt(
    script: Any,
    conversation_history: list[dict],
    lead_facts: dict,
    last_agent_message: str,
    conversation_stage: str = "hook",
) -> str:
    """Build the user prompt for a follow-up message when the lead has not replied."""
    cfg = _prompt_config()
    stage_cfg = get_stage_config(script, conversation_stage)
    stage_instructions = stage_cfg.get(
        "instructions",
        "Напиши короткое напоминание клиенту.",
    )
    stage_instructions = sanitize_context_text(stage_instructions, max_chars=700)
    max_length = get_max_length_for_stage(script, conversation_stage)
    cta_allowed = is_call_to_action_allowed(script, conversation_stage)
    cta_text = (
        sanitize_context_text(getattr(script, "call_to_action", None) or "")
        or "15-минутный созвон"
    )

    cta_note = (
        f"На этом этапе можно предложить {cta_text}."
        if cta_allowed
        else "На этом этапе НЕЛЬЗЯ предлагать созвон/встречу."
    )

    history_block = _build_history_block(conversation_history)
    facts_block = _build_facts_block(lead_facts)

    template = cfg.get("user_prompts", {}).get("follow_up", "")
    return _format_template(
        template,
        conversation_stage=conversation_stage,
        max_length=max_length,
        cta_note=cta_note,
        stage_instructions=stage_instructions,
        history_block=history_block,
        facts_block=facts_block,
        last_agent_message=sanitize_context_text(last_agent_message, max_chars=600),
    )


def build_intent_classification_prompt(message: str) -> str:
    cfg = _prompt_config()
    template = cfg.get("intent_classification_prompt", "")
    if not template:
        # Fallback to the previous hardcoded prompt if config is missing.
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

    return _format_template(template, message=message)
