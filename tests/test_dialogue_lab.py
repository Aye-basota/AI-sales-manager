from scripts.dialogue_lab import (
    DEFAULT_LIMIT,
    DEFAULT_SCENARIOS,
    _analyze_result,
)


def test_dialogue_lab_default_runs_thirty_scenarios():
    assert DEFAULT_LIMIT == 30
    assert len(DEFAULT_SCENARIOS) >= DEFAULT_LIMIT


def test_dialogue_lab_scenario_names_are_unique():
    names = [scenario["name"] for scenario in DEFAULT_SCENARIOS]
    assert len(names) == len(set(names))


def test_dialogue_lab_flags_unclosed_hard_refusal():
    issues = _analyze_result(
        scenario={
            "name": "hard_refusal",
            "lead": "Не пишите мне больше",
            "expected": {"negative"},
        },
        response_text="Могу уточнить, почему не интересно?",
        chunks=[],
        intent="objection",
        state="warm",
    )

    assert "hard refusal did not close conversation: warm" in issues
    assert "hard refusal response asked a follow-up question" in issues
