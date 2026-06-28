"""Sales funnel stage management."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_FUNNEL_STAGES: list[dict[str, Any]] = [
    {
        "stage": "hook",
        "goal": "Мягко зацепить внимание и сразу обозначить ценность.",
        "max_length": 200,
        "allow_call_to_action": False,
        "instructions": (
            "Напиши очень короткое первое сообщение (1-2 предложения). "
            "Сразу скажи, чем помогаем (например, оптимизируем международные платежи или снижаем комиссии). "
            "Не предлагай созвон, не задавай сложных вопросов. "
            "Избегай слов: анонимно, микшеры, P2P, незаметно, не светиться, обойти."
        ),
    },
    {
        "stage": "qualification",
        "goal": "Задать не более 1 вопроса и предложить демо/ценность.",
        "max_length": 350,
        "allow_call_to_action": False,
        "instructions": (
            "Задай РОВНО 1 короткий уточняющий вопрос о задаче клиента. "
            "Сразу после вопроса предложи короткую демо или созвон, чтобы показать, как работает решение. "
            "Не задавай второй вопрос. Не углубляйся в детали. "
            "Избегай подозрительной лексики: анонимно, микшеры, P2P, незаметно, не светиться, обойти."
        ),
    },
    {
        "stage": "value",
        "goal": "Кратко показать ценность и предложить созвон.",
        "max_length": 400,
        "allow_call_to_action": False,
        "instructions": (
            "Коротко объясни, как продукт решает озвученную проблему (1-2 конкретных пункта). "
            "Сразу предложи короткий созвон или демо, чтобы обсудить детали. "
            "Избегай подозрительной лексики: анонимно, микшеры, P2P, незаметно, не светиться, обойти."
        ),
    },
    {
        "stage": "cta",
        "goal": "Получить согласие на созвон/встречу.",
        "max_length": 400,
        "allow_call_to_action": True,
        "instructions": (
            "Предложи короткий созвон и 2 варианта времени (например, завтра 11:00 или 16:00). "
            "Если клиент уже согласен — уточни удобное время. "
            "Будь конкретным и дружелюбным."
        ),
    },
]


def get_funnel_stages(script: Any) -> list[dict[str, Any]]:
    """Return configured funnel stages or the default ones."""
    stages = getattr(script, "sales_funnel", None) or []
    if isinstance(stages, list) and stages:
        return stages
    return list(DEFAULT_FUNNEL_STAGES)


def get_stage_config(script: Any, stage: str) -> dict[str, Any]:
    """Return config for a specific funnel stage."""
    for s in get_funnel_stages(script):
        if s.get("stage") == stage:
            return s
    # Fallback to default stage with same name
    for s in DEFAULT_FUNNEL_STAGES:
        if s.get("stage") == stage:
            return s
    return DEFAULT_FUNNEL_STAGES[0]


def get_first_stage(script: Any) -> str:
    """Return the first stage to use for a new conversation."""
    configured = get_funnel_stages(script)
    first = configured[0].get("stage", "hook")
    first_message_goal = getattr(script, "first_message_goal", None)
    if first_message_goal and any(
        s.get("stage") == first_message_goal for s in configured
    ):
        return first_message_goal
    return first


def next_stage(script: Any, current_stage: str, intent: str | None = None) -> str:
    """Determine the next funnel stage based on current stage and lead intent."""
    stages = [s.get("stage") for s in get_funnel_stages(script)]
    if not stages:
        stages = ["hook", "qualification", "value", "cta"]

    if intent == "negative":
        return current_stage  # state_machine handles closure

    if intent == "meeting_intent":
        return "cta" if "cta" in stages else stages[-1]

    if current_stage not in stages:
        return stages[0]

    idx = stages.index(current_stage)
    if intent in ("positive", "question") and idx < len(stages) - 1:
        return stages[idx + 1]

    # For objection / informational stay on the same stage by default,
    # but move forward if the answer looks engaged.
    if intent in ("objection", "informational"):
        return current_stage

    return stages[min(idx + 1, len(stages) - 1)]


def get_max_length_for_stage(script: Any, stage: str) -> int:
    """Return max message length for a stage."""
    cfg = get_stage_config(script, stage)
    if cfg.get("max_length"):
        return int(cfg["max_length"])
    if stage == "hook":
        return getattr(script, "max_first_message_length", 200) or 200
    return 400


def is_call_to_action_allowed(script: Any, stage: str) -> bool:
    """Return True if the current stage may include a call to action."""
    cfg = get_stage_config(script, stage)
    return bool(cfg.get("allow_call_to_action", False))
