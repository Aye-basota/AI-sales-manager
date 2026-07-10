from app.logging_config import configure_logging


def test_app_logger_propagates_without_own_handlers():
    config = configure_logging("INFO")
    app_logger = config["loggers"]["app"]

    assert app_logger["handlers"] == []
    assert app_logger["propagate"] is True
