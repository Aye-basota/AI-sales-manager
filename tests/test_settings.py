from app.config.settings import Settings


def test_debug_accepts_release_profile():
    settings = Settings(debug="release")

    assert settings.debug is False


def test_debug_accepts_development_profile():
    settings = Settings(debug="development")

    assert settings.debug is True


def test_empty_telegram_api_id_uses_disabled_default():
    settings = Settings(telegram_api_id="")

    assert settings.telegram_api_id == 0


def test_empty_daily_message_limit_uses_default():
    settings = Settings(daily_message_limit="")

    assert settings.daily_message_limit == 50
