from tests.conftest import MockResult


def test_get_dashboard(client, mock_db, sample_campaign):
    mock_db.execute.side_effect = [
        MockResult([], scalar_value=42),                         # total_contacts
        MockResult([("draft", 5), ("running", 3)]),              # campaigns_by_status
        MockResult([(20, 100)]),                                 # reply_rate (replied, total)
        MockResult([], scalar_value=10),                         # qualified_count
        MockResult([], scalar_value=5),                          # meeting_booked_count
        MockResult([], scalar_value=120),                        # outbound_messages
        MockResult([], scalar_value=80),                         # inbound_messages
        MockResult([], scalar_value=3),                          # guardrails_rejected
        MockResult([], scalar_value=145.5),                      # avg_message_length
    ]
    response = client.get("/analytics/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_contacts"] == 42
    assert data["campaigns_by_status"] == {"draft": 5, "running": 3}
    assert data["reply_rate"] == 20.0
    assert data["qualified_count"] == 10
    assert data["meeting_booked_count"] == 5
    assert data["outbound_messages"] == 120
    assert data["inbound_messages"] == 80
    assert data["guardrails_rejected"] == 3
    assert data["avg_message_length"] == 145.5
