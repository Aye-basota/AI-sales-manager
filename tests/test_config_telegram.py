from app.config.telegram import is_configured_bot_token


def test_configured_bot_token_accepts_valid_botfather_shape():
    assert is_configured_bot_token("123456:ABC-def_123") is True


def test_configured_bot_token_rejects_empty_or_placeholder_values():
    assert is_configured_bot_token("") is False
    assert is_configured_bot_token("your_telegram_bot_token") is False


def test_configured_bot_token_rejects_invalid_shape():
    assert is_configured_bot_token("not-a-token") is False
