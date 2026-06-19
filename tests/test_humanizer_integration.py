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


def test_self_correction_disabled_by_default():
    text = "This is the original message."
    # Default rate is 0.0, so even with low random no self-correction is applied.
    with patch("app.core.humanizer.random.random", return_value=0.01):
        result = maybe_self_correct(text)
        assert result == text


def test_self_correction_respects_explicit_rate():
    text = "This is the original message."
    with patch("app.core.humanizer.random.random", return_value=0.01):
        with patch("app.core.humanizer.random.choice", return_value="Точнее, "):
            result = maybe_self_correct(text, rate=0.5)
            assert result != text
            assert "Точнее" in result

    with patch("app.core.humanizer.random.random", return_value=0.99):
        result = maybe_self_correct(text, rate=0.5)
        assert result == text


def test_typing_delay_zero_for_empty_text():
    assert calculate_typing_delay("") == 0
