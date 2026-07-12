"""Tests for facts extraction from inbound messages."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.conversation_service import extract_facts_from_message


@pytest.mark.asyncio
async def test_extract_facts_returns_empty_on_empty_text():
    result = await extract_facts_from_message("")
    assert result == {}


@pytest.mark.asyncio
async def test_extract_facts_returns_empty_when_llm_engine_unavailable():
    with patch("app.services.conversation_service.LLMEngine", None):
        result = await extract_facts_from_message("Some message")
    assert result == {}


@pytest.mark.asyncio
async def test_extract_facts_parses_json_response():
    mock_response = {
        "text": '{"company": "Acme", "role": "CEO", "pain": "low conversions", "budget": "50k$"}',
        "model": "gpt-4",
        "tokens_used": 10,
    }
    with patch("app.services.conversation_service.LLMEngine") as MockEngine:
        engine_inst = MockEngine.return_value
        engine_inst.generate_with_fallback = AsyncMock(return_value=mock_response)

        result = await extract_facts_from_message(
            "I am the CEO at Acme, struggling with low conversions, budget 50k$"
        )

    assert result["company"] == "Acme"
    assert result["role"] == "CEO"
    assert result["pain"] == "low conversions"
    assert result["budget"] == "50k$"


@pytest.mark.asyncio
async def test_extract_facts_strips_markdown_code_fence():
    mock_response = {
        "text": '```json\n{"company": "TestCorp", "city": "Moscow"}\n```',
        "model": "gpt-4",
        "tokens_used": 10,
    }
    with patch("app.services.conversation_service.LLMEngine") as MockEngine:
        engine_inst = MockEngine.return_value
        engine_inst.generate_with_fallback = AsyncMock(return_value=mock_response)

        result = await extract_facts_from_message("We are TestCorp from Moscow")

    assert result["company"] == "TestCorp"
    assert result["city"] == "Moscow"


@pytest.mark.asyncio
async def test_extract_facts_ignores_empty_values():
    mock_response = {
        "text": '{"company": "Acme", "role": "", "pain": "", "budget": ""}',
        "model": "gpt-4",
        "tokens_used": 10,
    }
    with patch("app.services.conversation_service.LLMEngine") as MockEngine:
        engine_inst = MockEngine.return_value
        engine_inst.generate_with_fallback = AsyncMock(return_value=mock_response)

        result = await extract_facts_from_message("I work at Acme")

    assert "company" in result
    assert "role" not in result
    assert "pain" not in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "llm_text",
    [
        "",
        "not json",
        '["not", "an", "object"]',
    ],
)
async def test_extract_facts_returns_empty_on_unusable_llm_output(llm_text):
    mock_response = {"text": llm_text}
    with patch("app.services.conversation_service.LLMEngine") as MockEngine:
        engine_inst = MockEngine.return_value
        engine_inst.generate_with_fallback = AsyncMock(return_value=mock_response)

        result = await extract_facts_from_message("Some message")

    assert result == {}


@pytest.mark.asyncio
async def test_extract_facts_graceful_on_llm_failure():
    with patch("app.services.conversation_service.LLMEngine") as MockEngine:
        engine_inst = MockEngine.return_value
        engine_inst.generate_with_fallback = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await extract_facts_from_message("Some message")

    assert result == {}
