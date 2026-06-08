import pytest

from app.core.state_machine import transition, is_terminal


class TestTransition:
    def test_cold_to_warm_on_initial_message(self):
        assert transition("cold", "initial_message") == "warm"

    def test_cold_to_hot_on_positive_reply(self):
        assert transition("cold", "positive_reply") == "hot"

    def test_cold_to_closed_on_negative_reply(self):
        assert transition("cold", "negative_reply") == "closed"

    def test_cold_to_follow_up_on_no_reply_24h(self):
        assert transition("cold", "no_reply_24h") == "follow_up"

    def test_cold_to_closed_on_no_reply_48h(self):
        assert transition("cold", "no_reply_48h") == "closed"

    def test_cold_to_meeting_booked_on_meeting_intent(self):
        assert transition("cold", "meeting_intent") == "meeting_booked"

    def test_cold_to_objection_handler_on_objection(self):
        assert transition("cold", "objection") == "objection_handler"

    def test_warm_to_hot_on_positive_reply(self):
        assert transition("warm", "positive_reply") == "hot"

    def test_warm_to_follow_up_on_no_reply_24h(self):
        assert transition("warm", "no_reply_24h") == "follow_up"

    def test_warm_to_closed_on_negative_reply(self):
        assert transition("warm", "negative_reply") == "closed"

    def test_hot_to_meeting_booked_on_meeting_intent(self):
        assert transition("hot", "meeting_intent") == "meeting_booked"

    def test_hot_to_closed_on_negative_reply(self):
        assert transition("hot", "negative_reply") == "closed"

    def test_hot_to_objection_handler_on_objection(self):
        assert transition("hot", "objection") == "objection_handler"

    def test_follow_up_to_hot_on_positive_reply(self):
        assert transition("follow_up", "positive_reply") == "hot"

    def test_follow_up_to_closed_on_no_reply_48h(self):
        assert transition("follow_up", "no_reply_48h") == "closed"

    def test_objection_handler_to_hot_on_positive_reply(self):
        assert transition("objection_handler", "positive_reply") == "hot"

    def test_objection_handler_to_closed_on_negative_reply(self):
        assert transition("objection_handler", "negative_reply") == "closed"

    def test_meeting_booked_is_terminal_no_transition(self):
        assert transition("meeting_booked", "positive_reply") == "meeting_booked"
        assert transition("meeting_booked", "initial_message") == "meeting_booked"

    def test_closed_is_terminal_no_transition(self):
        assert transition("closed", "positive_reply") == "closed"
        assert transition("closed", "initial_message") == "closed"

    def test_unknown_event_returns_current_state(self):
        assert transition("warm", "unknown_event") == "warm"

    def test_unknown_state_returns_current_state(self):
        assert transition("unknown", "initial_message") == "unknown"


class TestIsTerminal:
    def test_meeting_booked_is_terminal(self):
        assert is_terminal("meeting_booked") is True

    def test_closed_is_terminal(self):
        assert is_terminal("closed") is True

    def test_cold_is_not_terminal(self):
        assert is_terminal("cold") is False

    def test_warm_is_not_terminal(self):
        assert is_terminal("warm") is False

    def test_hot_is_not_terminal(self):
        assert is_terminal("hot") is False

    def test_follow_up_is_not_terminal(self):
        assert is_terminal("follow_up") is False

    def test_objection_handler_is_not_terminal(self):
        assert is_terminal("objection_handler") is False

    def test_unknown_state_is_not_terminal(self):
        assert is_terminal("unknown") is False
