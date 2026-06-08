import pytest

from app.llm.guardrails import (
    apply_guardrails,
    check_anti_repetition,
    check_length,
    check_no_forbidden_topics,
)


def test_check_length_within_limit():
    assert check_length("This is a short text.", max_words=300) is True


def test_check_length_exceeds_limit():
    long_text = "word " * 301
    assert check_length(long_text, max_words=300) is False


def test_check_no_forbidden_topics_default():
    assert check_no_forbidden_topics("Our SaaS is great.") is True
    assert check_no_forbidden_topics("Это политика и религия") is False


def test_check_no_forbidden_topics_custom():
    assert check_no_forbidden_topics("hello world", forbidden=["foo"]) is True
    assert check_no_forbidden_topics("hello foo", forbidden=["foo"]) is False


def test_check_anti_repetition_no_history():
    assert check_anti_repetition("Hello", []) is True


def test_check_anti_repetition_similar():
    prev = "Hello, how are you doing today?"
    curr = "Hello, how are you doing today?"
    assert check_anti_repetition(curr, [prev], threshold=0.8) is False


def test_check_anti_repetition_different():
    prev = "Hello, how are you doing today?"
    curr = "Goodbye, see you later!"
    assert check_anti_repetition(curr, [prev], threshold=0.8) is True


def test_apply_guardrails_passes():
    result = apply_guardrails("Valid message", ["Previous message"])
    assert result == "Valid message"


def test_apply_guardrails_fails_length():
    long_text = "word " * 301
    result = apply_guardrails(long_text, [])
    assert result is None


def test_apply_guardrails_fails_forbidden():
    result = apply_guardrails("Это политика", [])
    assert result is None


def test_apply_guardrails_fails_repetition():
    result = apply_guardrails("Same text", ["Same text"])
    assert result is None
