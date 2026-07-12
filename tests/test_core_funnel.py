"""Tests for sales funnel stage management."""

from unittest.mock import MagicMock, patch


from app.core.funnel import (
    DEFAULT_FUNNEL_STAGES,
    build_sales_funnel,
    get_first_stage,
    get_funnel_stages,
    get_max_length_for_stage,
    get_stage_config,
    infer_sales_strategy_from_funnel,
    is_call_to_action_allowed,
    next_stage,
    normalize_sales_strategy,
    sales_strategy_label,
)


class TestFunnelDefaults:
    def test_default_stages_have_expected_order(self):
        stages = [s["stage"] for s in DEFAULT_FUNNEL_STAGES]
        assert stages == ["trust", "engagement", "qualification", "value", "cta"]

    def test_trust_does_not_allow_cta(self):
        assert is_call_to_action_allowed(MagicMock(), "trust") is False

    def test_cta_allows_cta(self):
        assert is_call_to_action_allowed(MagicMock(), "cta") is True

    def test_qualification_does_not_allow_premature_cta(self):
        assert is_call_to_action_allowed(MagicMock(), "qualification") is False

    def test_default_trust_max_length(self):
        script = MagicMock(max_first_message_length=200)
        assert get_max_length_for_stage(script, "trust") == 200

    def test_legacy_hook_alias_maps_to_trust(self):
        script = MagicMock(max_first_message_length=200)
        assert get_max_length_for_stage(script, "hook") == 200
        assert is_call_to_action_allowed(script, "hook") is False

    def test_default_value_max_length(self):
        script = MagicMock(max_first_message_length=200)
        assert get_max_length_for_stage(script, "value") == 400

    def test_quick_call_strategy_allows_cta_after_interest(self):
        script = MagicMock(
            sales_funnel=build_sales_funnel("quick_call"),
            first_message_goal="trust",
        )
        assert next_stage(script, "trust", "positive") == "interest"
        assert is_call_to_action_allowed(script, "interest") is True

    def test_strategy_labels_are_localized(self):
        assert sales_strategy_label("quick_call", "ru") == "Быстрый созвон"
        assert sales_strategy_label("quick_call", "en") == "Quick call"
        assert normalize_sales_strategy("unknown") == "nurture"

    def test_infers_strategy_from_existing_funnel(self):
        assert infer_sales_strategy_from_funnel(build_sales_funnel("qualification")) == "qualification"
        assert infer_sales_strategy_from_funnel(build_sales_funnel("quick_call")) == "quick_call"
        assert infer_sales_strategy_from_funnel(build_sales_funnel("consultative")) == "consultative"
        assert infer_sales_strategy_from_funnel([{"stage": "handoff"}]) == "qualification"
        assert infer_sales_strategy_from_funnel([{"stage": "unknown"}]) == "nurture"
        assert infer_sales_strategy_from_funnel([]) == "nurture"


class TestCustomFunnel:
    def test_custom_funnel_is_used(self):
        script = MagicMock(
            sales_funnel=[
                {"stage": "greeting", "max_length": 100},
                {"stage": "pitch", "max_length": 500, "allow_call_to_action": True},
            ]
        )
        stages = get_funnel_stages(script)
        assert [s["stage"] for s in stages] == ["greeting", "pitch"]

    def test_first_stage_respects_first_message_goal(self):
        script = MagicMock(
            first_message_goal="value",
            sales_funnel=[
                {"stage": "trust"},
                {"stage": "value"},
            ],
        )
        assert get_first_stage(script) == "value"

    def test_first_stage_ignores_missing_first_message_goal(self):
        script = MagicMock(
            first_message_goal="missing",
            sales_funnel=[{"stage": "trust"}, {"stage": "value"}],
        )
        assert get_first_stage(script) == "trust"

    def test_empty_custom_funnel_falls_back_to_defaults(self):
        script = MagicMock(sales_funnel=[])
        assert get_funnel_stages(script)[0]["stage"] == "trust"

    def test_next_stage_advances_on_positive(self):
        script = MagicMock(sales_funnel=None)
        assert next_stage(script, "trust", "positive") == "engagement"

    def test_next_stage_advances_legacy_hook_alias(self):
        script = MagicMock(sales_funnel=None)
        assert next_stage(script, "hook", "positive") == "engagement"

    def test_next_stage_jumps_to_cta_on_meeting_intent(self):
        script = MagicMock(sales_funnel=None)
        assert next_stage(script, "trust", "meeting_intent") == "cta"

    def test_next_stage_stays_on_objection(self):
        script = MagicMock(sales_funnel=None)
        assert next_stage(script, "qualification", "objection") == "qualification"

    def test_next_stage_edge_cases(self):
        script = MagicMock(sales_funnel=[{"stage": "only"}])
        assert next_stage(script, "only", "negative") == "only"
        assert next_stage(script, "only", "meeting_intent") == "only"
        assert next_stage(script, "missing", None) == "only"
        assert next_stage(script, "only", "informational") == "only"
        assert next_stage(script, "only", None) == "only"


class TestStageConfig:
    def test_get_stage_config_returns_default_for_unknown(self):
        script = MagicMock(sales_funnel=None)
        cfg = get_stage_config(script, "unknown")
        assert cfg["stage"] == "trust"

    def test_stage_config_and_max_length_fallbacks(self):
        script = MagicMock(
            max_first_message_length=123,
            sales_funnel=[{"stage": "custom", "allow_call_to_action": True}],
        )
        assert get_stage_config(script, "custom")["stage"] == "custom"
        assert get_max_length_for_stage(script, "custom") == 400
        assert is_call_to_action_allowed(script, "custom") is True

    def test_stage_config_finds_default_stage_and_legacy_hook_length_fallback(self):
        script = MagicMock(max_first_message_length=123, sales_funnel=[{"stage": "custom"}])
        assert get_stage_config(script, "cta")["stage"] == "cta"

        with patch("app.core.funnel.get_stage_config", return_value={}):
            assert get_max_length_for_stage(script, "hook") == 123

    def test_next_stage_uses_defaults_when_stage_list_is_empty(self):
        script = MagicMock()
        with patch("app.core.funnel.get_funnel_stages", return_value=[]):
            assert next_stage(script, "missing", None) == "trust"
