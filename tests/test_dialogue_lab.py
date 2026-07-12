import pytest

from scripts.dialogue_lab import (
    CapturedSend,
    CapturingClient,
    CapturingNotifications,
    DEFAULT_LIMIT,
    DEFAULT_SCENARIOS,
    ScenarioResult,
    _analyze_result,
    _build_script,
    parse_args,
    write_report,
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


@pytest.mark.asyncio
async def test_dialogue_lab_capturing_client_records_transport_calls():
    client = CapturingClient()

    await client.read_history(123)
    await client.set_online()
    response = await client.send_message(123, "hello", typing_delay_ms=250)

    assert client.read_history_calls == 1
    assert client.set_online_calls == 1
    assert client.sends == [CapturedSend(user_id=123, text="hello", typing_delay_ms=250)]
    assert response == {"message_id": 1, "text": "hello"}


@pytest.mark.asyncio
async def test_dialogue_lab_capturing_notifications_records_hot_leads():
    from types import SimpleNamespace

    notifications = CapturingNotifications()
    contact = SimpleNamespace(id="contact-1")
    conversation = SimpleNamespace(id="conversation-1", current_state="hot")

    await notifications.send_hot_lead_alert(contact, conversation, "last message")

    assert notifications.hot_leads == [
        {
            "contact_id": "contact-1",
            "conversation_id": "conversation-1",
            "state": "hot",
            "last_message_text": "last message",
        }
    ]


def test_dialogue_lab_build_script_has_safe_defaults():
    script = _build_script("run-1")

    assert script.name == "Dialogue Lab run-1"
    assert script.timezone == "UTC"
    assert script.max_messages == 4
    assert script.is_active is True


def test_dialogue_lab_analyzer_flags_quality_regressions():
    issues = _analyze_result(
        scenario={
            "name": "spam_objection",
            "lead": "spam?",
            "expected": {"objection"},
        },
        response_text="Понимаю, давайте на 15-минутный созвон? Когда удобно?\n\nA\n\nB",
        chunks=[CapturedSend(user_id=1, text="x" * 451, typing_delay_ms=0)] * 4,
        intent="positive",
        state="warm",
    )

    assert "intent='positive' outside expected ['objection']" in issues
    assert "too many questions in one response" in issues
    assert "too many paragraph breaks" in issues
    assert "too many Telegram chunks: 4" in issues
    assert "a Telegram chunk is too long" in issues
    assert "missing typing delay for at least one chunk" in issues
    assert "robotic opening" in issues
    assert "premature meeting CTA" in issues
    assert "risk concern was not addressed" in issues


def test_dialogue_lab_analyzer_flags_bot_meeting_and_pricing_cases():
    bot_issues = _analyze_result(
        scenario={"name": "bot_check", "lead": "bot?", "expected": {"question"}},
        response_text="Я бот, помогу вам",
        chunks=[CapturedSend(user_id=1, text="Я бот, помогу вам", typing_delay_ms=100)],
        intent="question",
        state="warm",
    )
    assert "bot_check response reveals automation" in bot_issues

    meeting_issues = _analyze_result(
        scenario={"name": "meeting_intent", "lead": "call", "expected": {"meeting_intent"}},
        response_text="Когда удобно?",
        chunks=[CapturedSend(user_id=1, text="Когда удобно?", typing_delay_ms=100)],
        intent="meeting_intent",
        state="warm",
    )
    assert "meeting intent did not become hot/meeting_booked: warm" in meeting_issues

    pricing_issues = _analyze_result(
        scenario={
            "name": "pricing_question",
            "lead": "price?",
            "expected": {"question"},
        },
        response_text="Это стоит 1000$",
        chunks=[CapturedSend(user_id=1, text="Это стоит 1000$", typing_delay_ms=100)],
        intent="question",
        state="warm",
    )
    assert "pricing response invented an exact price" in pricing_issues


def test_dialogue_lab_write_report_serializes_results(tmp_path):
    output = tmp_path / "dialogue-lab.md"
    result = ScenarioResult(
        name="scenario",
        lead_text="lead",
        response_text="response",
        chunks=[CapturedSend(user_id=1, text="response", typing_delay_ms=100)],
        intent="question",
        state="warm",
        stage="engagement",
        notifications=0,
        issues=["issue"],
    )

    write_report([result], output)

    text = output.read_text(encoding="utf-8")
    assert "# Dialogue Lab Report" in text
    assert "Scenarios: 1" in text
    assert "FAIL: scenario" in text
    assert "typing_delay_ms=100" in text
    assert "- issue" in text


def test_dialogue_lab_parse_args(monkeypatch, tmp_path):
    output = tmp_path / "report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "dialogue_lab.py",
            "--lead-id",
            "1000",
            "--limit",
            "2",
            "--keep-db",
            "--output",
            str(output),
        ],
    )

    args = parse_args()

    assert args.lead_id == 1000
    assert args.limit == 2
    assert args.keep_db is True
    assert args.output == output
