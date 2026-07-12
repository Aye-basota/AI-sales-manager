from types import SimpleNamespace

from app.core.initial_message_quality import (
    build_safe_initial_fallback,
    needs_initial_message_retry,
)


def test_safe_initial_fallback_uses_script_business_context():
    contact = SimpleNamespace(first_name="Максим")
    script = SimpleNamespace(
        role_prompt="Поставляем бумажные стаканчики для кофеен и небольших сетей.",
        goal="Предложить образцы",
        target_audience="Кофейни",
    )

    text = build_safe_initial_fallback(contact, script)

    assert "Привет, Максим" in text
    assert "стаканчики" in text
    assert "лидогенерац" not in text.lower()


def test_initial_retry_detects_bad_markers_and_safe_fallback_defaults():
    assert needs_initial_message_retry("Как у вас в Рогах и копытах устроен стек?")
    assert not needs_initial_message_retry("Привет, пишу коротко.")

    assert "Привет." in build_safe_initial_fallback()


def test_initial_retry_detects_fake_personalization():
    assert needs_initial_message_retry(
        "Привет, Максим. Работаешь в IT — наверное, знаешь, как важно отдыхать."
    )
    assert needs_initial_message_retry(
        "Знакомы с Газпромбанком — уважаю ваш подход к качеству и деталям."
    )
    assert not needs_initial_message_retry(
        "У нас бархатные, нежные, ласковые руки лучших массажисток города."
    )


def test_safe_initial_fallback_uses_goal_or_audience_and_truncates_long_text():
    long_role = "Очень длинное описание " * 20
    contact = SimpleNamespace(first_name=None)
    script = SimpleNamespace(
        role_prompt=long_role,
        goal="Назначить созвон",
        target_audience="Кофейни",
    )

    text = build_safe_initial_fallback(contact, script)

    assert "…" in text
    assert "Привет." in text

    script = SimpleNamespace(role_prompt="", goal="Назначить созвон", target_audience="")
    fallback = build_safe_initial_fallback(contact, script)
    assert "Назначить созвон" not in fallback
    assert "без лишней ручной рутины" in fallback


def test_safe_initial_fallback_uses_generic_context_when_script_fields_empty():
    script = SimpleNamespace(role_prompt="", goal="", target_audience="")

    text = build_safe_initial_fallback(SimpleNamespace(first_name="Анна"), script)

    assert "Анна" in text
    assert "без лишней ручной рутины" in text
