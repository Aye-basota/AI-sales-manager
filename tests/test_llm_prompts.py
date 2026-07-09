from unittest.mock import MagicMock


from app.llm.prompts import (
    build_initial_user_prompt,
    build_intent_classification_prompt,
    build_system_prompt,
    build_user_prompt,
)


def test_build_system_prompt_with_all_fields():
    script = MagicMock()
    script.role_prompt = "Ты senior sales manager."
    script.target_audience = "IT директора"
    script.goal = "Продать SaaS."
    script.success_criteria = "Подписка на демо."
    script.tone = "friendly"

    prompt = build_system_prompt(script, company_name="TestCorp")

    assert "TestCorp" in prompt
    assert "senior sales manager" in prompt
    assert "IT директора" in prompt
    assert "Продать SaaS" in prompt
    assert "Подписка на демо" in prompt
    assert "friendly" in prompt
    assert "ПРАВИЛА ГЕНЕРАЦИИ" in prompt


def test_build_system_prompt_defaults():
    script = MagicMock()
    script.role_prompt = None
    script.target_audience = None
    script.goal = None
    script.success_criteria = None
    script.tone = None

    prompt = build_system_prompt(script)

    assert "Neural Lead" in prompt
    assert "Целевая аудитория" not in prompt
    assert "professional" in prompt


def test_build_user_prompt():
    history = [
        {"role": "user", "content": "Привет"},
        {"role": "assistant", "content": "Здравствуйте!"},
    ]
    facts = {"company": "Acme", "position": "CEO"}
    last_agent = "Здравствуйте!"
    lead_msg = "Расскажите о вашем продукте"

    prompt = build_user_prompt(history, facts, last_agent, lead_msg)

    assert "Привет" in prompt
    assert "Здравствуйте!" in prompt
    assert "Acme" in prompt
    assert "CEO" in prompt
    assert "Расскажите о вашем продукте" in prompt


def test_initial_prompt_asks_for_human_like_opening():
    script = MagicMock()
    script.sales_funnel = None
    script.max_first_message_length = 200
    contact = MagicMock()
    contact.first_name = "Максим"
    contact.company_name = "Рога и копыта"
    contact.position = "CTO"
    contact.city = None
    contact.industry = None

    prompt = build_initial_user_prompt(script, contact)

    assert "без рекламного слогана" in prompt
    assert "как у вас в" in prompt
    assert "в вашем стеке" in prompt
    assert "Задай один простой вопрос" in prompt


def test_build_intent_classification_prompt():
    prompt = build_intent_classification_prompt("Я заинтересован")

    assert "meeting_intent" in prompt
    assert "question" in prompt
    assert "objection" in prompt
    assert "positive" in prompt
    assert "negative" in prompt
    assert "informational" in prompt
    assert 'Сообщение: "Я заинтересован"' in prompt
    assert "Метка:" in prompt


def test_system_prompt_no_markdown_rule():
    script = MagicMock()
    script.role_prompt = None
    script.target_audience = None
    script.goal = None
    script.success_criteria = None
    script.tone = None

    prompt = build_system_prompt(script)
    assert "Никогда не используй markdown" in prompt
    assert "Пиши plain text" in prompt


def test_system_prompt_no_bot_rule():
    script = MagicMock()
    script.role_prompt = None
    script.target_audience = None
    script.goal = None
    script.success_criteria = None
    script.tone = None

    prompt = build_system_prompt(script)
    assert "Никогда не признавайся" in prompt
    assert "что ты бот или ИИ" in prompt


def test_system_prompt_includes_nurturing_rules():
    script = MagicMock()
    script.role_prompt = None
    script.target_audience = None
    script.goal = None
    script.success_criteria = None
    script.tone = None

    prompt = build_system_prompt(script)

    assert "ПРИНЦИПЫ LEAD NURTURING" in prompt
    assert "{nurturing_rules}" not in prompt
    assert "{ nurturing_rules }" not in prompt
