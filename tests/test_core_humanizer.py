from unittest.mock import patch


from app.core.humanizer import (
    add_casual_markers,
    calculate_thinking_delay,
    calculate_typing_delay,
    contains_markdown,
    format_message,
    maybe_double_take,
    maybe_self_correct,
    remove_markdown,
    split_message_into_chunks,
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
        text = "a" * 50
        delay = calculate_typing_delay(text, chars_per_min=(300, 300))
        expected = int((50 / 5) * 1000)
        assert delay == expected

    def test_typing_delay_is_capped(self):
        text = "a" * 1000
        delay = calculate_typing_delay(text, chars_per_min=(300, 300))
        assert delay <= 10000

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
        assert any(
            result.startswith(p)
            for p in [
                "Точнее, ",
                "*точнее, ",
                "Уточню, ",
                "*уточню, ",
                "Поправка, ",
                "*поправка, ",
            ]
        )

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
        assert any(
            marker.lower() in result.lower()
            for marker in ["кстати", "слушайте", "если честно"]
        )

    def test_single_sentence_gets_marker(self):
        text = "This is a single sentence."
        with patch("app.core.humanizer.random.random", return_value=0.01):
            result = add_casual_markers(text, rate=0.15)
        assert any(
            marker.lower() in result.lower()
            for marker in ["кстати", "слушайте", "если честно"]
        )

    def test_multiple_sentences_only_one_marker(self):
        text = "First sentence. Second sentence. Third sentence."
        with patch("app.core.humanizer.random.random", return_value=0.01):
            result = add_casual_markers(text, rate=0.15)
        # Should have exactly one marker added
        count = sum(
            result.lower().count(marker)
            for marker in ["кстати", "слушайте", "если честно"]
        )
        assert count == 1

    def test_no_change_when_random_above_rate(self):
        text = "Hello. How are you?"
        with patch("app.core.humanizer.random.random", return_value=0.99):
            result = add_casual_markers(text, rate=0.15)
        assert result == text


class TestMaybeDoubleTake:
    def test_no_city_returns_original(self):
        text = "Hello there"
        assert maybe_double_take(text, city=None, rate=1.0) == text

    def test_no_injection_when_rate_zero(self):
        text = "Hello there"
        assert maybe_double_take(text, city="Moscow", rate=0.0) == text

    def test_injects_city_question_when_rate_one(self):
        text = "Hello there"
        result = maybe_double_take(text, city="Moscow", rate=1.0)
        assert "Moscow" in result
        assert result.startswith(text)


class TestContainsMarkdown:
    def test_no_markdown(self):
        assert contains_markdown("Просто текст.") is False

    def test_has_hash(self):
        assert contains_markdown("# заголовок") is True

    def test_has_asterisk(self):
        assert contains_markdown("**жирный**") is True

    def test_has_backtick(self):
        assert contains_markdown("`код`") is True


class TestRemoveMarkdown:
    def test_remove_bold(self):
        assert remove_markdown("**жирный**") == "жирный"

    def test_remove_italic(self):
        assert remove_markdown("_курсив_") == "курсив"

    def test_remove_backticks(self):
        assert remove_markdown("`код`") == "код"

    def test_remove_header(self):
        assert remove_markdown("# Заголовок") == "Заголовок"

    def test_remove_stray_asterisks(self):
        assert remove_markdown("*точнее, ") == "точнее, "

    def test_plain_text_unchanged(self):
        assert remove_markdown("Просто текст.") == "Просто текст."


class TestFormatMessage:
    def test_empty_string(self):
        assert format_message("") == ""

    def test_removes_markdown(self):
        result = format_message("**жирный** текст `код`", city=None)
        assert "**" not in result
        assert "`" not in result
        assert "жирный" in result
        assert "код" in result

    def test_no_aggressive_humanization_by_default(self):
        # By default self-correction, markers and double-take are disabled.
        with patch("app.core.humanizer.random.random", return_value=0.01):
            result = format_message("Hello. How are you?", city=None)
        assert result == "Hello. How are you?"

    def test_no_double_take_by_default(self):
        with patch("app.core.humanizer.random.random", return_value=0.01):
            result = format_message("Hello there", city="Moscow")
        assert "Moscow" not in result
        assert result == "Hello there"


class TestSplitMessageIntoChunks:
    def test_empty_text_returns_empty(self):
        assert split_message_into_chunks("") == []

    def test_short_text_single_chunk(self):
        assert split_message_into_chunks("Hello there") == ["Hello there"]

    def test_long_paragraph_split_by_sentences(self):
        text = "First sentence. " * 20
        chunks = split_message_into_chunks(text, max_chars=100)
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)

    def test_paragraphs_preserved_when_small(self):
        text = "Paragraph one.\n\nParagraph two."
        chunks = split_message_into_chunks(text, max_chars=200)
        assert len(chunks) == 1
        assert "Paragraph one" in chunks[0]
        assert "Paragraph two" in chunks[0]

    def test_max_chunks_does_not_drop_tail_text(self):
        text = "\n\n".join(f"Part {idx}" for idx in range(1, 8))
        chunks = split_message_into_chunks(text, max_chars=20, max_chunks=3)

        joined = "\n\n".join(chunks)
        for idx in range(1, 8):
            assert f"Part {idx}" in joined
        assert len(chunks) == 3
