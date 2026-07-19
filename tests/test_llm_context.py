from types import SimpleNamespace

from app.llm.context import build_verified_context_block, extract_offer_summary


def test_offer_summary_preserves_user_offer_copy():
    script = SimpleNamespace(
        name="Элитный массаж",
        role_prompt=(
            "Предоставляем услуги массажа. У нас самые лучшие массажистки Москвы. "
            "Бархатные нежные ласковые."
        ),
        target_audience="",
        goal="",
        success_criteria="",
        call_to_action="",
    )

    text = extract_offer_summary(script)

    assert "Бархатные нежные ласковые" in text


def test_verified_context_preserves_discount_address_and_cta():
    script = SimpleNamespace(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа.",
        target_audience="",
        goal=(
            "Пригласить и назначить демонстрацию продукта в салоне со скидкой 20%. "
            "Адрес улица Университетская корпус 1, цокольный этаж."
        ),
        success_criteria="Клиент согласился прийти.",
        call_to_action="Прийти в наш салон и протестировать качество услуг",
    )

    block = build_verified_context_block(script)

    assert "скидкой 20%" in block
    assert "Университетская" in block
    assert "Прийти в наш салон" in block


def test_verified_context_includes_owner_business_details():
    script = SimpleNamespace(
        name="Стаканчики",
        role_prompt="Поставляем пластиковые стаканчики.",
        target_audience="Кофейни",
        goal="Назначить созвон.",
        success_criteria="Лид согласился обсудить поставку.",
        call_to_action="Короткий созвон",
        business_details={
            "answers": {
                "delivery": "Доставка по Москве 1-2 дня, регионы через ТК.",
            },
        },
    )

    block = build_verified_context_block(script)

    assert "Проверенные уточнения владельца" in block
    assert "Доставка по Москве 1-2 дня" in block
