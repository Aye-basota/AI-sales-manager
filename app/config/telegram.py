import re


_BOT_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]+$")
_PLACEHOLDER_TOKENS = {
    "your_telegram_bot_token",
    "ваш_токен_от_botfather",
    "replace_me",
    "changeme",
}


def is_configured_bot_token(token: str | None) -> bool:
    if not token:
        return False

    normalized = token.strip()
    if normalized.lower() in _PLACEHOLDER_TOKENS:
        return False

    return bool(_BOT_TOKEN_RE.fullmatch(normalized))
