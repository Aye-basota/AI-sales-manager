from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.intent_classifier import classify_intent


@pytest.mark.asyncio
async def test_classify_intent_exact_label():
    engine = MagicMock()
    engine.generate_with_fallback = AsyncMock(return_value={"text": "meeting_intent"})

    result = await classify_intent("Давайте встретимся", engine)
    assert result == "meeting_intent"


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
        return_value={"text": "Похоже, это objection к цене"}
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
