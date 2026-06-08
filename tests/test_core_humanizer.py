import random
from unittest.mock import patch

import pytest

from app.core.humanizer import (
    calculate_typing_delay,
    calculate_thinking_delay,
    maybe_self_correct,
    add_casual_markers,
)


class TestCalculateTypingDelay:
    def test_empty_string_returns_zero(self):
        assert calculate_typing_delay("") == 0

    def test_short_text_within_reasonable_range(self):
        text = "hello"
        delay = calculate_typing_delay(text, chars_per_min=(300, 300))
        expected = int((len(text) / (300 / 60)) * 1000)
        assert delay == expected

    def test_longer_text_takes_longer(self):
        text = "a" * 100
        delay = calculate_typing_delay(text, chars_per_min=(300, 300))
        expected = int((100 / 5) * 1000)
        assert delay == expected

    def test_random_speed_affects_delay(self):
        text = "test"
        with patch("app.core.humanizer.random.uniform", return_value=200):
            delay = calculate_typing_delay(text, chars_per_min=(200, 350))
        assert delay == int((4 / (200 / 60)) * 1000)


class TestCalculateThinkingDelay:
    def test_default_range(self):
        with patch("app.core.humanizer.random.randint", return_value=5):
            assert calculate_thinking_delay() == 5000

    def test_custom_range(self):
        with patch("app.core.humanizer.random.randint", return_value=10):
            assert calculate_thinking_delay(min_sec=5, max_sec=20) == 10000


class TestMaybeSelfCorrect:
    def test_no_correction_when_rate_is_zero(self):
        text = "This is a message"
        assert maybe_self_correct(text, rate=0.0) == text

    def test_always_correct_when_rate_is_one(self):
        text = "This is a message"
        result = maybe_self_correct(text, rate=1.0)
        assert result != text
        assert any(result.startswith(p) for p in ["Точнее, ", "*точнее, ", "Уточню, ", "*уточню, ", "Поправка, ", "*поправка, "])

    def test_empty_string_returns_empty(self):
        assert maybe_self_correct("", rate=1.0) == ""

    def test_correction_prepended(self):
        with patch("app.core.humanizer.random.random", return_value=0.01):
            result = maybe_self_correct("hello", rate=0.06)
        assert result != "hello"
        assert result.endswith("hello")


class TestAddCasualMarkers:
    def test_no_marker_when_rate_is_zero(self):
        text = "Hello. How are you?"
        assert add_casual_markers(text, rate=0.0) == text

    def test_empty_string_returns_empty(self):
        assert add_casual_markers("", rate=1.0) == ""

    def test_marker_injected_when_rate_is_one(self):
        text = "Hello. How are you?"
        result = add_casual_markers(text, rate=1.0)
        assert any(marker in result for marker in ["кстати", "слушайте", "если честно"])

    def test_single_sentence_gets_marker(self):
        text = "This is a single sentence."
        with patch("app.core.humanizer.random.random", return_value=0.01):
            result = add_casual_markers(text, rate=0.15)
        assert any(marker in result for marker in ["кстати", "слушайте", "если честно"])

    def test_multiple_sentences_only_one_marker(self):
        text = "First sentence. Second sentence. Third sentence."
        with patch("app.core.humanizer.random.random", return_value=0.01):
            result = add_casual_markers(text, rate=0.15)
        # Should have exactly one marker added
        count = sum(result.count(marker) for marker in ["кстати", "слушайте", "если честно"])
        assert count == 1

    def test_no_change_when_random_above_rate(self):
        text = "Hello. How are you?"
        with patch("app.core.humanizer.random.random", return_value=0.99):
            result = add_casual_markers(text, rate=0.15)
        assert result == text
