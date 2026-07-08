from app.config.settings import Settings


def test_debug_accepts_release_profile():
    settings = Settings(debug="release")

    assert settings.debug is False


def test_debug_accepts_development_profile():
    settings = Settings(debug="development")

    assert settings.debug is True
