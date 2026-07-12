from app.config.settings import Settings


def test_debug_accepts_release_profile():
    settings = Settings(debug="release")

    assert settings.debug is False


def test_debug_accepts_development_profile():
    settings = Settings(debug="development")

    assert settings.debug is True


def test_sql_echo_is_disabled_by_default():
    settings = Settings()

    assert settings.sql_echo is False


def test_sql_echo_accepts_bool_strings():
    settings = Settings(sql_echo="yes")

    assert settings.sql_echo is True


def test_empty_telegram_api_id_uses_disabled_default():
    settings = Settings(telegram_api_id="")

    assert settings.telegram_api_id == 0


def test_empty_daily_message_limit_uses_default():
    settings = Settings(daily_message_limit="")

    assert settings.daily_message_limit == 50


def test_unknown_bool_string_is_left_for_pydantic_validation():
    assert Settings.parse_bool_flag("maybe") == "maybe"
