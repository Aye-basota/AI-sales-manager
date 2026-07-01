"""Tests for sales funnel stage management."""

from unittest.mock import MagicMock


from app.core.funnel import (
    DEFAULT_FUNNEL_STAGES,
    get_first_stage,
    get_funnel_stages,
    get_max_length_for_stage,
    get_stage_config,
    is_call_to_action_allowed,
    next_stage,
)


class TestFunnelDefaults:
    def test_default_stages_have_expected_order(self):
        stages = [s["stage"] for s in DEFAULT_FUNNEL_STAGES]
        assert stages == ["trust", "engagement", "qualification", "value", "cta"]

    def test_trust_does_not_allow_cta(self):
        assert is_call_to_action_allowed(MagicMock(), "trust") is False

    def test_cta_allows_cta(self):
        assert is_call_to_action_allowed(MagicMock(), "cta") is True

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


class TestStageConfig:
    def test_get_stage_config_returns_default_for_unknown(self):
        script = MagicMock(sales_funnel=None)
        cfg = get_stage_config(script, "unknown")
        assert cfg["stage"] == "trust"
