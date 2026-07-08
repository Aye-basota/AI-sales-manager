from app.llm.guardrails import (
    GuardrailsResult,
    apply_guardrails,
    check_anti_repetition,
    check_length,
    check_no_bot_words,
    check_no_forbidden_topics,
    check_no_markdown,
    check_no_emoji,
    evaluate_guardrails,
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


class TestCheckNoBotWords:
    def test_clean_text(self):
        assert check_no_bot_words("Здравствуйте, хотел уточнить детали.") is True

    def test_detects_bot(self):
        assert check_no_bot_words("Я бот и помогу вам") is False

    def test_detects_assistant(self):
        assert check_no_bot_words("Я ваш ассистент") is False

    def test_detects_ai(self):
        assert check_no_bot_words("Я искусственный интеллект") is False

    def test_detects_neural_network(self):
        assert check_no_bot_words("Я нейросеть") is False

    def test_detects_ya_ii(self):
        assert check_no_bot_words("я ИИ") is False


class TestCheckNoMarkdown:
    def test_plain_text_passes(self):
        assert check_no_markdown("Просто текст без форматирования.") is True

    def test_hash_fails(self):
        assert check_no_markdown("# Заголовок") is False

    def test_asterisk_fails(self):
        assert check_no_markdown("**жирный**") is False

    def test_underscore_fails(self):
        assert check_no_markdown("_курсив_") is False

    def test_backtick_fails(self):
        assert check_no_markdown("`код`") is False


class TestCheckNoEmoji:
    def test_plain_text_passes(self):
        assert check_no_emoji("Просто текст без эмодзи.") is True

    def test_common_emoji_fails(self):
        assert check_no_emoji("Привет 🙂") is False


class TestGuardrailsResult:
    def test_eq_with_str_when_approved(self):
        gr = GuardrailsResult(approved=True, text="hello", violations=[])
        assert gr == "hello"

    def test_eq_with_none_when_rejected(self):
        gr = GuardrailsResult(approved=False, text=None, violations=["length"])
        assert gr == None  # noqa: E711

    def test_eq_with_guardrails_result(self):
        gr1 = GuardrailsResult(approved=True, text="ok", violations=[])
        gr2 = GuardrailsResult(approved=True, text="ok", violations=[])
        assert gr1 == gr2


class TestEvaluateGuardrails:
    def test_approved(self):
        result = evaluate_guardrails("Valid message", ["Previous"])
        assert result.approved is True
        assert result.text == "Valid message"
        assert result.violations == []

    def test_rejected_length(self):
        long_text = "word " * 301
        result = evaluate_guardrails(long_text, [])
        assert result.approved is False
        assert "length" in result.violations

    def test_rejected_bot_words(self):
        result = evaluate_guardrails("Я бот, чем могу помочь?", [])
        assert result.approved is False
        assert "bot_words" in result.violations

    def test_rejected_markdown(self):
        result = evaluate_guardrails("**жирный текст**", [])
        assert result.approved is False
        assert "markdown" in result.violations

    def test_multiple_violations(self):
        bad_text = "# политика и я бот"
        result = evaluate_guardrails(bad_text, [])
        assert result.approved is False
        assert set(result.violations) >= {"forbidden_topic", "bot_words", "markdown"}
