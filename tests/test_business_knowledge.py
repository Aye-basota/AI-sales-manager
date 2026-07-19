from types import SimpleNamespace

from app.core.business_knowledge import (
    audit_questions_from_details,
    business_details_prompt_block,
    build_business_audit_messages,
    detect_clarification_need,
    detect_unsupported_claim,
    fallback_business_context_questions,
    business_audit_has_owner_answer,
    has_verified_detail,
    looks_like_high_commercial_intent,
    mark_audit_answered,
    merge_owner_answer,
    missing_business_context_questions,
    parse_business_audit_questions,
    store_audit_questions,
    verified_detail_excerpt,
)


def _script(**overrides):
    base = {
        "name": "Пластиковые стаканчики",
        "role_prompt": "Поставляем пластиковые стаканчики для кофеен.",
        "target_audience": "Кофейни и общепит",
        "goal": "Предложить поставку со скидкой 20% и выйти на короткий созвон.",
        "success_criteria": "Лид согласился обсудить условия.",
        "call_to_action": "Короткий созвон",
        "business_details": {},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_discount_mention_does_not_make_pricing_verified():
    script = _script()

    question_keys = {area.key for area in missing_business_context_questions(script)}

    assert "pricing" in question_keys
    assert "delivery" in question_keys
    assert has_verified_detail(script, "pricing") is False
    assert detect_clarification_need(script, "Сколько стоит партия 10000 штук?").key == "pricing"


def test_owner_answer_becomes_verified_context_and_stops_price_clarification():
    details = merge_owner_answer(
        {},
        "Цена от 3 руб за штуку, минимальный заказ 5000 штук.",
        category="pricing",
        question="Какие цены можно называть?",
    )
    script = _script(business_details=details)

    assert has_verified_detail(script, "pricing") is True
    assert detect_clarification_need(script, "Сколько стоит партия 10000 штук?") is None
    assert "Цена от 3 руб" in business_details_prompt_block(script)


def test_owner_note_with_minimum_budget_verifies_pricing():
    script = _script(
        business_details={
            "owner_notes": [
                {
                    "text": (
                        "Минимальный бюджет — от $3 000, сложные проекты "
                        "оцениваются индивидуально."
                    ),
                }
            ],
        }
    )

    assert has_verified_detail(script, "pricing") is True
    assert detect_clarification_need(script, "А что по расценкам?") is None
    assert "от $3 000" in verified_detail_excerpt(script, "pricing")


def test_unsupported_claim_is_blocked_until_owner_confirms_area():
    script = _script()

    unsupported = detect_unsupported_claim(
        script,
        "Да, есть все необходимые сертификаты и закрывающие документы.",
    )

    assert unsupported.key == "documents"

    details = merge_owner_answer(
        {},
        "Есть сертификаты соответствия и закрывающие документы для юрлиц.",
        category="documents",
        question="Какие документы есть?",
    )
    script = _script(business_details=details)

    assert detect_unsupported_claim(
        script,
        "Да, есть все необходимые сертификаты и закрывающие документы.",
    ) is None


def test_high_commercial_intent_detects_volume_and_urgency():
    assert looks_like_high_commercial_intent("Нужно 200000 стаканов к пятнице")
    assert looks_like_high_commercial_intent("Берем 500 тысяч в месяц, дадите скидку?")
    assert not looks_like_high_commercial_intent("Можете рассказать подробнее?")


def test_llm_business_audit_prompt_uses_current_draft():
    script = _script(role_prompt="Печатаем логотипы на стаканчиках для кофеен.")

    messages = build_business_audit_messages(script)
    prompt_text = "\n".join(message["content"] for message in messages)

    assert "Печатаем логотипы на стаканчиках" in prompt_text
    assert "от 3 до 6" in prompt_text
    assert '{"questions"' in prompt_text


def test_parse_business_audit_questions_accepts_json_and_drops_generic():
    raw = (
        '{"questions":["Какие цены?",'
        '"Какой минимальный тираж для стаканчиков с логотипом можно обещать кофейням?",'
        '"Какие сроки печати логотипа на стаканчиках называем для первой поставки?"]}'
    )

    questions = parse_business_audit_questions(raw)

    assert questions == [
        "Какой минимальный тираж для стаканчиков с логотипом можно обещать кофейням?",
        "Какие сроки печати логотипа на стаканчиках называем для первой поставки?",
    ]


def test_audit_questions_are_stored_and_reused_from_business_details():
    questions = [
        "Какой минимальный заказ стаканчиков можно обещать кофейням?",
        "Какие сроки доставки стаканчиков в Москву можно назвать?",
    ]

    details = store_audit_questions({}, questions, source="unit-test")

    assert audit_questions_from_details(details) == questions
    assert details["audit"]["source"] == "unit-test"


def test_audit_answer_marker_stops_repeating_initial_questions():
    details = store_audit_questions(
        {},
        ["Какой минимальный заказ стаканчиков можно обещать кофейням?"],
        source="unit-test",
    )

    assert business_audit_has_owner_answer(details) is False
    answered = mark_audit_answered(details)

    assert business_audit_has_owner_answer(answered) is True


def test_fallback_business_questions_still_reference_offer():
    script = _script(role_prompt="Поставляем стаканчики с логотипом для кофеен.")

    questions = fallback_business_context_questions(script, limit=2)

    assert questions
    assert "стаканчики" in questions[0].lower()
