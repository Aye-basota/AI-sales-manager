from types import SimpleNamespace

from app.core.initial_message_quality import build_safe_initial_fallback


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
