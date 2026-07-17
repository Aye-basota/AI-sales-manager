from types import SimpleNamespace

from app.core.follow_up_quality import (
    build_follow_up_retry_prompt,
    build_safe_follow_up_fallback,
    needs_follow_up_retry,
)


def test_follow_up_retry_detects_second_first_touch_patterns():
    assert needs_follow_up_retry("Привет, Максим. Если вдруг интересно, расскажу подробнее.")
    assert needs_follow_up_retry("Могу рассказать подробнее, если актуально.")


def test_follow_up_retry_detects_repeated_previous_message():
    previous = (
        "Пишу коротко: помогаем аккуратно начинать диалоги с потенциальными "
        "клиентами без лишней ручной рутины."
    )
    current = (
        "Пишу коротко: помогаем аккуратно начинать диалоги с потенциальными "
        "клиентами без лишней ручной рутины."
    )

    assert needs_follow_up_retry(current, previous)


def test_follow_up_retry_allows_short_specific_nudge():
    text = "Максим, оставлю тут коротко: если сейчас неактуально, больше не отвлекаю."
    assert needs_follow_up_retry(text, "Привет, Максим. Пишу по поводу заявок.") is False


def test_follow_up_retry_prompt_contains_hard_rules():
    prompt = build_follow_up_retry_prompt("Привет, расскажу подробнее", "Привет")

    assert "не начинай с приветствия" in prompt
    assert "не повторяй предыдущую реплику" in prompt
    assert "если вдруг интересно" in prompt


def test_safe_follow_up_fallback_uses_name_and_offer():
    contact = SimpleNamespace(first_name="Максим")
    script = SimpleNamespace(
        role_prompt="Предоставляем сервис для аккуратной обработки лидов",
        name="Lead tool",
    )

    text = build_safe_follow_up_fallback(contact, script)

    assert text.startswith("Максим, ")
    assert "аккуратной обработки лидов" in text
    assert "больше не буду отвлекать" in text
