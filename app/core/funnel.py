"""Sales funnel stage management."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_FUNNEL_STAGES: list[dict[str, Any]] = [
    {
        "stage": "trust",
        "goal": "Мягко представиться и показать, что ты понимаешь контекст клиента.",
        "max_length": 200,
        "allow_call_to_action": False,
        "instructions": (
            "Напиши очень короткое первое сообщение (1-2 предложения). "
            "Сразу скажи, чем помогает компания, но не продавай. "
            "Не предлагай созвон, не задавай сложных вопросов. "
            "Избегай слов: анонимно, микшеры, P2P, незаметно, не светиться, обойти."
        ),
    },
    {
        "stage": "engagement",
        "goal": "Ответить на интерес клиента и не превращать диалог в анкету.",
        "max_length": 300,
        "allow_call_to_action": False,
        "instructions": (
            "Сначала ответь на смысл сообщения клиента. "
            "Если без уточнения нельзя продолжить, задай 1 короткий вопрос. "
            "Если контекста уже достаточно, не задавай новый вопрос по инерции. "
            "Не предлагай созвон и не рассказывай о продукте подробно. "
            "Избегай подозрительной лексики: анонимно, микшеры, P2P, незаметно, не светиться, обойти."
        ),
    },
    {
        "stage": "qualification",
        "goal": "Ответить по делу и дать полезный следующий кусок контекста без давления.",
        "max_length": 350,
        "allow_call_to_action": False,
        "instructions": (
            "Ответь на вопрос клиента коротко и по сути. "
            "Если человек проявил интерес, лучше коротко объясни механику или опиши пример словами, без созвона. "
            "Не устраивай допрос и не задавай второй вопрос подряд. "
            "Избегай подозрительной лексики: анонимно, микшеры, P2P, незаметно, не светиться, обойти."
        ),
    },
    {
        "stage": "value",
        "goal": "Кратко показать ценность и подготовить к CTA.",
        "max_length": 400,
        "allow_call_to_action": False,
        "instructions": (
            "Коротко объясни, как продукт решает озвученную проблему (1-2 конкретных пункта). "
            "Если вопрос клиента уже закрыт, опиши пример или механику словами без давления. "
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
            "Не предлагай созвон или встречу как способ просто узнать цену, адрес или базовые условия. "
            "Будь конкретным и дружелюбным."
        ),
    },
]

SALES_STRATEGY_TEMPLATES: dict[str, dict[str, Any]] = {
    "nurture": {
        "label_ru": "Бережный прогрев",
        "label_en": "Careful nurture",
        "description_ru": (
            "Сначала доверие и короткая польза, созвон только после явного интереса."
        ),
        "description_en": (
            "Build trust and value first; offer a call only after clear interest."
        ),
        "stages": DEFAULT_FUNNEL_STAGES,
    },
    "quick_call": {
        "label_ru": "Быстрый созвон",
        "label_en": "Quick call",
        "description_ru": (
            "Для понятного оффера: при интересе или вопросе быстро переводит в короткий созвон."
        ),
        "description_en": (
            "For simple offers: move to a short call once the lead shows interest or asks a question."
        ),
        "stages": [
            {
                "stage": "trust",
                "goal": "Мягко представиться и обозначить пользу без давления.",
                "max_length": 220,
                "allow_call_to_action": False,
                "instructions": (
                    "Напиши 1-2 коротких предложения. Не продавай агрессивно и не задавай сложных вопросов. "
                    "Если уместно, закончи мягкой фразой вроде «если актуально, расскажу в двух словах»."
                ),
            },
            {
                "stage": "interest",
                "goal": "Ответить на интерес и быстро предложить безопасный следующий шаг.",
                "max_length": 320,
                "allow_call_to_action": True,
                "instructions": (
                    "Сначала коротко ответь на реплику клиента. Если интерес уже есть, предложи короткий созвон "
                    "или уточнение с менеджером без давления. Если человек спрашивает цену, адрес или базовые условия, "
                    "сначала закрой этот вопрос и не зови на встречу ради ответа. Не устраивай анкету."
                ),
            },
            {
                "stage": "cta",
                "goal": "Согласовать удобное время и остановиться.",
                "max_length": 360,
                "allow_call_to_action": True,
                "instructions": (
                    "Предложи короткий созвон и 1-2 варианта времени. "
                    "Если клиент назвал время, подтверди и остановись. "
                    "После согласования не задавай новые квалификационные вопросы."
                ),
            },
        ],
    },
    "consultative": {
        "label_ru": "Консультативная продажа",
        "label_en": "Consultative sale",
        "description_ru": (
            "SPIN-подход: понять ситуацию, проблему и пользу, но без допроса."
        ),
        "description_en": (
            "SPIN-inspired: understand situation, problem, and value without interrogating the lead."
        ),
        "stages": [
            {
                "stage": "trust",
                "goal": "Мягко начать и показать релевантность.",
                "max_length": 220,
                "allow_call_to_action": False,
                "instructions": (
                    "Коротко обозначь, почему пишешь. Не делай вид, что знаешь внутреннюю ситуацию клиента. "
                    "Можно предложить объяснить в двух словах."
                ),
            },
            {
                "stage": "situation",
                "goal": "Понять текущий контекст клиента одним легким вопросом.",
                "max_length": 320,
                "allow_call_to_action": False,
                "instructions": (
                    "Ответь на сообщение и задай максимум один простой вопрос только если он нужен. "
                    "Не спрашивай подряд про бюджет, сроки и ЛПР."
                ),
            },
            {
                "stage": "problem",
                "goal": "Связать озвученную ситуацию с возможной проблемой и ценностью.",
                "max_length": 360,
                "allow_call_to_action": False,
                "instructions": (
                    "Аккуратно переформулируй вводные как гипотезу, не утверждай слишком уверенно. "
                    "Дай небольшой полезный контекст, без выдуманных кейсов и цифр."
                ),
            },
            {
                "stage": "value",
                "goal": "Показать пользу и предложить следующий шаг, если интерес уже есть.",
                "max_length": 380,
                "allow_call_to_action": True,
                "instructions": (
                    "Если интерес подтвержден, предложи короткий созвон или следующий шаг. "
                    "Если данных мало, сначала честно скажи, что нужно сверить вводные. "
                    "Не используй созвон как замену ответа на вопрос о цене или базовых условиях."
                ),
            },
            {
                "stage": "cta",
                "goal": "Согласовать созвон и остановиться.",
                "max_length": 360,
                "allow_call_to_action": True,
                "instructions": (
                    "Согласуй удобное время. После согласия не продолжай продавать и не задавай новые вопросы."
                ),
            },
        ],
    },
    "qualification": {
        "label_ru": "Квалификация ЛПР",
        "label_en": "Decision-maker qualification",
        "description_ru": (
            "BANT/MEDDIC-lite: бережно понять потребность, роль, сроки и передать человеку."
        ),
        "description_en": (
            "BANT/MEDDIC-lite: qualify need, role, timing, and hand off to a human."
        ),
        "stages": [
            {
                "stage": "trust",
                "goal": "Начать диалог без давления и объяснить релевантность.",
                "max_length": 220,
                "allow_call_to_action": False,
                "instructions": (
                    "Напиши коротко и спокойно. Не спрашивай сразу бюджет или кто принимает решение."
                ),
            },
            {
                "stage": "need",
                "goal": "Понять, есть ли реальная потребность.",
                "max_length": 330,
                "allow_call_to_action": False,
                "instructions": (
                    "Ответь по делу и мягко проверь потребность одним вопросом, если без него нельзя продолжить. "
                    "Не звучать как анкета."
                ),
            },
            {
                "stage": "authority_timing",
                "goal": "Бережно понять роль человека и примерные сроки.",
                "max_length": 360,
                "allow_call_to_action": False,
                "instructions": (
                    "Если нужно понять ЛПР или сроки, спроси это в человеческой форме и только один пункт за раз. "
                    "Не дави на бюджет."
                ),
            },
            {
                "stage": "handoff",
                "goal": "Передать подходящего лида менеджеру через созвон/контакт.",
                "max_length": 380,
                "allow_call_to_action": True,
                "instructions": (
                    "Если лид подходит или просит детали, предложи короткий созвон "
                    "с человеком, который ответит предметно. "
                    "Не обещай то, чего нет в контексте. Если вопрос только про цену или базовые условия, "
                    "не назначай встречу вместо ответа."
                ),
            },
            {
                "stage": "cta",
                "goal": "Согласовать время и остановиться.",
                "max_length": 360,
                "allow_call_to_action": True,
                "instructions": (
                    "Подтверди время или предложи 1-2 варианта. После согласования остановись."
                ),
            },
        ],
    },
}

SALES_STRATEGY_ALIASES = {
    "careful_nurture": "nurture",
    "consultative_sale": "consultative",
    "quick": "quick_call",
    "fast_call": "quick_call",
    "bant": "qualification",
    "meddic": "qualification",
}

# Backward-compatible alias mapping for legacy stage names stored in the database.
_LEGACY_STAGE_ALIASES: dict[str, str] = {
    "hook": "trust",
    "warm": "engagement",
}


def get_funnel_stages(script: Any) -> list[dict[str, Any]]:
    """Return configured funnel stages or the default ones."""
    stages = getattr(script, "sales_funnel", None) or []
    if isinstance(stages, list) and stages:
        return stages
    return list(DEFAULT_FUNNEL_STAGES)


def normalize_sales_strategy(strategy_key: str | None) -> str:
    """Return a supported sales strategy key."""
    key = (strategy_key or "nurture").strip().lower()
    key = SALES_STRATEGY_ALIASES.get(key, key)
    if key not in SALES_STRATEGY_TEMPLATES:
        return "nurture"
    return key


def build_sales_funnel(strategy_key: str | None) -> list[dict[str, Any]]:
    """Build a fresh funnel config for the selected sales strategy."""
    key = normalize_sales_strategy(strategy_key)
    return deepcopy(SALES_STRATEGY_TEMPLATES[key]["stages"])


def sales_strategy_label(strategy_key: str | None, lang: str = "ru") -> str:
    """Human-readable strategy label for admin UI."""
    key = normalize_sales_strategy(strategy_key)
    template = SALES_STRATEGY_TEMPLATES[key]
    return template["label_en"] if lang == "en" else template["label_ru"]


def infer_sales_strategy_from_funnel(stages: Any) -> str:
    """Best-effort strategy detection for existing scripts."""
    if not isinstance(stages, list) or not stages:
        return "nurture"
    stage_names = [str(stage.get("stage", "")) for stage in stages if isinstance(stage, dict)]
    if "interest" in stage_names:
        return "quick_call"
    if "situation" in stage_names or "problem" in stage_names:
        return "consultative"
    if "authority_timing" in stage_names or "handoff" in stage_names:
        return "qualification"
    return "nurture"


def _normalize_stage(stage: str) -> str:
    """Map legacy stage names to the current lead-nurturing stages."""
    return _LEGACY_STAGE_ALIASES.get(stage, stage)


def get_stage_config(script: Any, stage: str) -> dict[str, Any]:
    """Return config for a specific funnel stage."""
    stage = _normalize_stage(stage)
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
    first = configured[0].get("stage", "trust")
    first_message_goal = getattr(script, "first_message_goal", None)
    if first_message_goal:
        first_message_goal = _normalize_stage(first_message_goal)
        if any(s.get("stage") == first_message_goal for s in configured):
            return first_message_goal
    return first


def next_stage(script: Any, current_stage: str, intent: str | None = None) -> str:
    """Determine the next funnel stage based on current stage and lead intent."""
    current_stage = _normalize_stage(current_stage)
    stages = [s.get("stage") for s in get_funnel_stages(script)]
    if not stages:
        stages = [s["stage"] for s in DEFAULT_FUNNEL_STAGES]

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
