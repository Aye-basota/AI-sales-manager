"""Tests for humanizer integration (delays and self-correction)."""

from unittest.mock import patch

import pytest

from app.core.humanizer import (
    calculate_typing_delay,
    calculate_thinking_delay,
    maybe_self_correct,
)


def test_typing_delay_scales_with_text_length():
    short_text = "Hi"
    long_text = "Hi, this is a much longer message with many characters."
    short_delay = calculate_typing_delay(short_text)
    long_delay = calculate_typing_delay(long_text)
    assert long_delay > short_delay
    assert short_delay >= 0


def test_thinking_delay_within_range():
    for _ in range(50):
        delay = calculate_thinking_delay()
        assert 3000 <= delay <= 15000


def test_self_correction_probability_with_mock_random():
    text = "This is the original message."
    with patch("app.core.humanizer.random.random", return_value=0.01):
        with patch("app.core.humanizer.random.choice", return_value="Точнее, "):
            result = maybe_self_correct(text)
            assert result != text
            # Check for Russian self-correction keywords (with or without asterisk)
            keywords = [
                "\u0422\u043e\u0447\u043d\u0435\u0435",
                "\u0423\u0442\u043e\u0447\u043d\u044e",
                "\u041f\u043e\u043f\u0440\u0430\u0432\u043a\u0430",
            ]
            assert any(kw in result for kw in keywords)

    with patch("app.core.humanizer.random.random", return_value=0.99):
        result = maybe_self_correct(text)
        assert result == text


def test_typing_delay_zero_for_empty_text():
    assert calculate_typing_delay("") == 0
