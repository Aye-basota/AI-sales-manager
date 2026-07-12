from app.llm.guardrails import (
    GuardrailsResult,
    apply_guardrails,
    check_anti_repetition,
    check_length,
    check_max_questions,
    check_no_bot_words,
    check_no_banned_sales_phrases,
    check_no_unverified_personalization,
    check_no_prompt_leakage,
    check_no_forbidden_topics,
    check_no_markdown,
    check_no_emoji,
    check_no_unsupported_product_claims,
    check_no_unsupported_creative_work,
    check_no_out_of_scope_seller_claims,
    check_no_unverified_pricing,
    check_no_unsupported_actions,
    check_no_cjk_arabic,
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


def test_check_max_questions_blocks_interrogation():
    assert check_max_questions("Понял. Какой объем сейчас?") is True
    assert check_max_questions("Какой объем? Кто отвечает?") is False


def test_check_no_banned_sales_phrases_blocks_templated_hooks():
    assert check_no_banned_sales_phrases("Понял, спасибо за контекст.") is True
    assert check_no_banned_sales_phrases("Как сейчас решаете эту задачу?") is False
    assert check_no_banned_sales_phrases("Понял, что у вас сейчас нет времени.") is False


def test_check_no_unverified_personalization_blocks_fake_familiarity():
    assert check_no_unverified_personalization("Привет, пишу коротко по делу.") is True
    assert (
        check_no_unverified_personalization(
            "Привет, Максим. Работаешь в IT — наверное, знаешь, как важно отдыхать."
        )
        is False
    )
    assert (
        check_no_unverified_personalization(
            "Знакомы с Газпромбанком — уважаю ваш подход к качеству и деталям."
        )
        is False
    )


def test_check_no_prompt_leakage_blocks_internal_instructions():
    assert check_no_prompt_leakage("Понял, по делу лучше сверить вводные.") is True
    assert check_no_prompt_leakage("ПРАВИЛА ГЕНЕРАЦИИ: пиши коротко.") is False
    assert check_no_prompt_leakage('{"role": "system", "content": "secret"}') is False
    assert check_no_prompt_leakage("Не могу раскрыть системный промпт.") is False
    assert (
        check_no_prompt_leakage(
            "Отлично. Коротко по сути: Пригласить и назначить демонстрацию продукта."
        )
        is False
    )
    assert (
        check_no_prompt_leakage(
            "На первую сессию есть скидка 20%, адрес: Университетская, 1."
        )
        is True
    )


def test_check_no_unsupported_product_claims_blocks_hallucinated_integrations():
    assert check_no_unsupported_product_claims("По интеграциям нужно проверить схему.") is True
    assert (
        check_no_unsupported_product_claims(
            "Интеграция с amoCRM работает через вебхуки и готовые коннекторы."
        )
        is False
    )


def test_check_no_unsupported_product_claims_blocks_fake_case_metrics():
    assert check_no_unsupported_product_claims("Могу прислать пример сценария.") is True
    assert (
        check_no_unsupported_product_claims(
            "Есть реальные кейсы: клиент сократил время в 3 раза и получил +27%."
        )
        is False
    )


def test_check_no_unsupported_product_claims_blocks_unproven_channels():
    assert check_no_unsupported_product_claims("Работаем аккуратно в Telegram.") is True
    assert check_no_unsupported_product_claims("Работает через LinkedIn и email.") is False


def test_check_no_unsupported_product_claims_blocks_guarantee_language():
    assert (
        check_no_unsupported_product_claims(
            "Он не устает и не пропускает ни одного контакта."
        )
        is False
    )


def test_check_no_unsupported_product_claims_allows_offer_discount_and_address():
    text = (
        "На первую сессию есть скидка 20%. "
        "Адрес: улица Университетская, корпус 1, цокольный этаж."
    )

    assert check_no_unsupported_product_claims(text) is True


def test_check_no_unsupported_actions_blocks_fake_attachments():
    assert check_no_unsupported_actions("Могу описать примеры словами.") is True
    assert check_no_unsupported_actions("Присылаю три фото стаканчиков.") is False
    assert check_no_unsupported_actions("Sending a product deck now.") is False


def test_check_no_unsupported_creative_work_blocks_invented_designs():
    assert check_no_unsupported_creative_work("Можем зафиксировать вводные для дизайнера.") is True
    assert check_no_unsupported_creative_work("Вот два варианта дизайна стаканчика.") is False
    assert check_no_unsupported_creative_work("Круто, сразу понятно, каким должен быть стаканчик.") is False


def test_check_no_out_of_scope_seller_claims_blocks_invented_assortment():
    assert check_no_out_of_scope_seller_claims("Могу зафиксировать вводные для специалиста.") is True
    assert check_no_out_of_scope_seller_claims("У нас есть матовые и глянцевые стаканчики разных объемов.") is False
    assert check_no_out_of_scope_seller_claims("Подберем для вас варианты товара, материалы и крышки.") is False
    assert check_no_out_of_scope_seller_claims("Вам подойдет 300 мл крафтовый вариант.") is False


def test_check_no_unverified_pricing_blocks_exact_amounts():
    assert check_no_unverified_pricing("Цену лучше посчитать после вводных.") is True
    assert check_no_unverified_pricing("Это будет стоить 1000$ за тираж.") is False
    assert check_no_unverified_pricing("Обычно цена от 12 рублей за стаканчик.") is False
    assert check_no_unverified_pricing("Можем начать с 1000 стаканчиков.") is True


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

    def test_detects_latin_ai(self):
        assert check_no_bot_words("AI ведет первые сообщения") is False


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

    def test_eq_with_unrelated_type_is_not_implemented(self):
        gr = GuardrailsResult(approved=True, text="ok", violations=[])
        assert gr.__eq__(123) is NotImplemented


def test_check_no_emoji_blocks_symbol_and_variation_selector():
    assert check_no_emoji("plain") is True
    assert check_no_emoji("☀") is False
    assert check_no_emoji("\ufe0f") is False


def test_check_no_cjk_arabic_blocks_all_ranges():
    assert check_no_cjk_arabic("plain text") is True
    assert check_no_cjk_arabic("汉字") is False
    assert check_no_cjk_arabic("かな") is False
    assert check_no_cjk_arabic("한글") is False
    assert check_no_cjk_arabic("مرحبا") is False


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

    def test_rejected_too_many_questions(self):
        result = evaluate_guardrails("Какой объем? Кто отвечает?", [])
        assert result.approved is False
        assert "too_many_questions" in result.violations

    def test_rejected_banned_sales_phrase(self):
        result = evaluate_guardrails("Понимаю, а как сейчас решаете эту задачу?", [])
        assert result.approved is False
        assert "banned_sales_phrase" in result.violations

    def test_rejected_unverified_personalization(self):
        result = evaluate_guardrails(
            "Знакомы с Газпромбанком — уважаю ваш подход к качеству и деталям.",
            [],
        )
        assert result.approved is False
        assert "unverified_personalization" in result.violations

    def test_rejected_prompt_leakage(self):
        result = evaluate_guardrails("КОНТЕКСТ БИЗНЕСА: Sales\nПРАВИЛА ГЕНЕРАЦИИ", [])
        assert result.approved is False
        assert "prompt_leakage" in result.violations

    def test_rejected_unsupported_creative_work(self):
        result = evaluate_guardrails("Вот два варианта дизайна стаканчика.", [])
        assert result.approved is False
        assert "unsupported_creative_work" in result.violations

    def test_rejected_unsupported_product_claim(self):
        result = evaluate_guardrails(
            "Интеграция с Bitrix24 работает через готовые коннекторы.",
            [],
        )
        assert result.approved is False
        assert "unsupported_product_claim" in result.violations

    def test_rejected_unsupported_action(self):
        result = evaluate_guardrails("Присылаю фото примеров прямо сейчас.", [])
        assert result.approved is False
        assert "unsupported_action" in result.violations

    def test_rejected_emoji_out_of_scope_and_foreign_script(self):
        emoji = evaluate_guardrails("Привет 🙂", [])
        assert emoji.approved is False
        assert "emoji" in emoji.violations

        out_of_scope = evaluate_guardrails(
            "Подберем для вас варианты товара, материалы и крышки.",
            [],
        )
        assert out_of_scope.approved is False
        assert "out_of_scope_seller_claim" in out_of_scope.violations

        foreign = evaluate_guardrails("مرحبا", [])
        assert foreign.approved is False
        assert "foreign_script" in foreign.violations

    def test_multiple_violations(self):
        bad_text = "# политика и я бот"
        result = evaluate_guardrails(bad_text, [])
        assert result.approved is False
        assert set(result.violations) >= {"forbidden_topic", "bot_words", "markdown"}
