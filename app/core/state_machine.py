"""Lead funnel state machine."""

from typing import Literal

State = Literal[
    "cold",
    "warm",
    "hot",
    "meeting_booked",
    "closed",
    "follow_up",
    "objection_handler",
]

Event = Literal[
    "initial_message",
    "positive_reply",
    "negative_reply",
    "no_reply_24h",
    "no_reply_48h",
    "meeting_intent",
    "objection",
]

_TRANSITIONS: dict[State, dict[Event, State]] = {
    "cold": {
        "initial_message": "warm",
        "positive_reply": "hot",
        "negative_reply": "closed",
        "no_reply_24h": "follow_up",
        "no_reply_48h": "closed",
        "meeting_intent": "meeting_booked",
        "objection": "objection_handler",
    },
    "warm": {
        "positive_reply": "hot",
        "negative_reply": "closed",
        "no_reply_24h": "follow_up",
        "no_reply_48h": "closed",
        "meeting_intent": "meeting_booked",
        "objection": "objection_handler",
    },
    "hot": {
        "positive_reply": "hot",
        "negative_reply": "closed",
        "no_reply_24h": "follow_up",
        "no_reply_48h": "closed",
        "meeting_intent": "meeting_booked",
        "objection": "objection_handler",
    },
    "follow_up": {
        "positive_reply": "hot",
        "negative_reply": "closed",
        "no_reply_24h": "follow_up",
        "no_reply_48h": "closed",
        "meeting_intent": "meeting_booked",
        "objection": "objection_handler",
    },
    "objection_handler": {
        "positive_reply": "hot",
        "negative_reply": "closed",
        "no_reply_24h": "follow_up",
        "no_reply_48h": "closed",
        "meeting_intent": "meeting_booked",
        "objection": "objection_handler",
    },
    "meeting_booked": {},
    "closed": {},
}

_TERMINAL_STATES: set[State] = {"meeting_booked", "closed"}


def transition(current_state: str, event: str) -> str:
    """Return the new state after applying *event* to *current_state*.

    If the event is not defined for the current state, the state remains
    unchanged.
    """
    state_map = _TRANSITIONS.get(current_state, {})
    return state_map.get(event, current_state)


def is_terminal(state: str) -> bool:
    """Return True if *state* is a terminal state."""
    return state in _TERMINAL_STATES
