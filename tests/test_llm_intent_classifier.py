from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.intent_classifier import classify_intent


@pytest.mark.asyncio
async def test_classify_intent_exact_label():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(return_value={"text": "meeting_intent"})

    result = await classify_intent("Расскажите подробнее", engine)
    assert result == "meeting_intent"
    engine.generate_with_fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_classify_intent_hard_refusal_is_rule_based_negative():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(return_value={"text": "objection"})

    result = await classify_intent("Не пишите мне больше, нам это не нужно.", engine)

    assert result == "negative"
    engine.generate_with_fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_classify_intent_one_word_no_is_rule_based_negative():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(return_value={"text": "informational"})

    result = await classify_intent("Нет", engine)

    assert result == "negative"
    engine.generate_with_fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_classify_intent_meeting_is_rule_based():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(return_value={"text": "positive"})

    result = await classify_intent("Ок, давайте созвон завтра после обеда.", engine)

    assert result == "meeting_intent"
    engine.generate_with_fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_classify_intent_with_punctuation():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(
        return_value={"text": 'Метка: "positive"!'}
    )

    result = await classify_intent("Интересно", engine)
    assert result == "positive"


@pytest.mark.asyncio
async def test_classify_intent_substring_match():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(
        return_value={"text": "Похоже, это maybe_objection_case к цене"}
    )

    result = await classify_intent("Слишком дорого", engine)
    assert result == "objection"


@pytest.mark.asyncio
async def test_classify_intent_unknown_defaults_to_informational():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(
        return_value={"text": "что-то непонятное"}
    )

    result = await classify_intent("Бла бла бла", engine)
    assert result == "informational"


@pytest.mark.asyncio
async def test_classify_intent_prompt_structure():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(return_value={"text": "question"})

    await classify_intent("Сколько стоит?", engine)

    args, kwargs = engine.generate_with_fallback.call_args
    messages = args[0]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Сколько стоит?" in messages[1]["content"]
