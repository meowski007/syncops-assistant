"""
Unit Tests for Local Slack Mock Mode and Alert Cooldown Logic.
Validates zero-credential execution and simulated event formatting.
"""

import pytest
from app.slack.mock import MockSlackClient
from app.slack.bot import reset_alert_cooldown
from scripts.seed_data import seed_database

@pytest.fixture(scope="module")
def slack_db(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("slack") / "slack_test.db"
    seed_database(db_path=db_file)
    return db_file

def test_slack_mock_syncstatus_command(slack_db):
    client = MockSlackClient(db_path=slack_db)
    res = client.execute_slash_command("/syncstatus")
    
    assert res["command"] == "/syncstatus"
    assert res["mode"] == "SIMULATED_SLACK_MOCK"
    assert "blocks" in res
    assert len(res["blocks"]) > 0
    assert "[SIMULATED SLACK]" in res["text"]

def test_slack_mock_incidents_command(slack_db):
    client = MockSlackClient(db_path=slack_db)
    res = client.execute_slash_command("/incidents")
    
    assert res["command"] == "/incidents"
    assert res["mode"] == "SIMULATED_SLACK_MOCK"
    assert "blocks" in res
    assert res["incident_count"] > 0

def test_slack_mock_unknown_command(slack_db):
    client = MockSlackClient(db_path=slack_db)
    res = client.execute_slash_command("/unknowncmd")
    
    assert "error" in res
    assert "Available" in res["error"]

def test_slack_mock_app_mention_health(slack_db):
    client = MockSlackClient(db_path=slack_db)
    res = client.simulate_app_mention("@SyncOps How is platform sync health?")
    
    assert res["mode"] == "SIMULATED_SLACK_MOCK"
    assert "Current synthetic sync success rate" in res["response_text"]
    assert res["sync_success_rate"] > 0.0

def test_slack_mock_app_mention_triage(slack_db):
    client = MockSlackClient(db_path=slack_db)
    res = client.simulate_app_mention("@SyncOps triage INC-2026-1001")
    
    assert res["mode"] == "SIMULATED_SLACK_MOCK"
    assert "triage_result" in res
    assert res["triage_result"]["incident_id"] == "INC-2026-1001"
    assert "Triage Assessment" in res["response_text"]

def test_slack_mock_threshold_alert_and_cooldown(slack_db):
    reset_alert_cooldown()
    client = MockSlackClient(db_path=slack_db)
    
    # 1. Trigger with threshold lower than 24h failure rate (approx 4.9%)
    alert1 = client.trigger_threshold_check(threshold=0.01, cooldown_minutes=15, window_hours=24)
    assert alert1["mode"] == "SIMULATED_SLACK_MOCK"
    assert alert1["alert_triggered"] is True
    assert alert1["in_cooldown"] is False

    # 2. Immediate second call should be caught by cooldown
    alert2 = client.trigger_threshold_check(threshold=0.01, cooldown_minutes=15, window_hours=24)
    assert alert2["alert_triggered"] is False
    assert alert2["in_cooldown"] is True
