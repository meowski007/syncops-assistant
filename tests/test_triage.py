"""
Unit and Integration Tests for SRE Triage Agent, Tools, and Deterministic Fallback.
Validates Pydantic schemas, runbook file retrieval, and offline fallback behavior.
"""

import pytest
from app.config import RUNBOOKS_DIR
from app.triage.tools import tool_get_incident_details, tool_search_and_read_runbook, execute_tool
from app.triage.fallback import run_deterministic_triage
from app.triage.agent import triage_incident
from app.schemas import TriageResult
from scripts.seed_data import seed_database

@pytest.fixture(scope="module")
def triage_db(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("triage") / "triage_test.db"
    seed_database(db_path=db_file)
    return db_file

def test_tool_get_incident_details(triage_db):
    res = tool_get_incident_details("INC-2026-1001", db_path=triage_db)
    assert res.get("id") == "INC-2026-1001"
    assert res.get("affected_cohort") == "iOS-Production"
    assert "cohort_telemetry" in res

def test_tool_get_incident_details_missing(triage_db):
    res = tool_get_incident_details("NON_EXISTENT_INC", db_path=triage_db)
    assert res.get("status") == "NOT_FOUND"

def test_tool_search_and_read_runbook_exact():
    res = tool_search_and_read_runbook("sync_failures.md")
    assert res.get("status") == "SUCCESS"
    assert "sync_failures.md" in res.get("filename")
    assert "Symptoms & Detection" in res.get("content")

def test_tool_search_and_read_runbook_keyword():
    res = tool_search_and_read_runbook("auth")
    assert res.get("status") == "SUCCESS"
    assert "authentication_errors.md" in res.get("filename")

def test_tool_search_and_read_runbook_nonexistent():
    res = tool_search_and_read_runbook("completely_unrelated_query_xyz")
    assert "available_runbooks" in res

def test_execute_tool_wrapper(triage_db):
    json_out = execute_tool("get_incident_details", {"incident_id": "INC-2026-1001"}, db_path=triage_db)
    assert "INC-2026-1001" in json_out

    unknown_out = execute_tool("unknown_tool", {})
    assert "Unknown tool" in unknown_out

def test_deterministic_fallback_payload_timeout(triage_db):
    result = run_deterministic_triage("INC-2026-1001", db_path=triage_db)
    assert isinstance(result, TriageResult)
    assert result.incident_id == "INC-2026-1001"
    assert result.analysis_mode == "deterministic_fallback"
    assert result.requires_human_review is True
    assert "PAYLOAD_TIMEOUT" in result.likely_cause
    assert len(result.evidence) > 0
    assert "payload_timeout_guide.md" in result.runbook_references

    # Verify runbook reference exists on disk
    for ref in result.runbook_references:
        assert (RUNBOOKS_DIR / ref).exists()

def test_deterministic_fallback_firmware(triage_db):
    result = run_deterministic_triage("INC-2026-1002", db_path=triage_db)
    assert result.incident_id == "INC-2026-1002"
    assert "FIRMWARE_UNSUPPORTED" in result.likely_cause
    assert "firmware_update_failures.md" in result.runbook_references

def test_deterministic_fallback_missing_incident(triage_db):
    result = run_deterministic_triage("INC-MISSING-9999", db_path=triage_db)
    assert result.incident_id == "INC-MISSING-9999"
    assert "not found" in result.summary.lower()
    assert result.confidence <= 0.2

def test_triage_incident_forced_fallback(triage_db):
    # Verify that triage_incident with force_fallback returns clean Pydantic model
    res = triage_incident("INC-2026-1003", force_fallback=True, db_path=triage_db)
    assert res.incident_id == "INC-2026-1003"
    assert res.analysis_mode == "deterministic_fallback"
    assert res.confidence > 0.5

def test_triage_incident_llm_tool_calling_mocked(triage_db):
    """
    Validates that when an OpenAI client is configured, the agent executes
    the tool-calling loop (calling get_incident_details) and formats a valid TriageResult.
    """
    import json
    from unittest.mock import MagicMock, patch

    mock_client = MagicMock()
    # Turn 1: Model requests tool execution
    tc = MagicMock()
    tc.id = "call_mock_123"
    tc.function.name = "get_incident_details"
    tc.function.arguments = json.dumps({"incident_id": "INC-2026-1001"})
    msg1 = MagicMock()
    msg1.tool_calls = [tc]
    msg1.content = None
    choice1 = MagicMock(message=msg1)
    resp1 = MagicMock(choices=[choice1])

    # Turn 2: Model returns final structured assessment
    msg2 = MagicMock()
    msg2.tool_calls = None
    msg2.content = json.dumps({
        "summary": "Triage investigation verified via LLM tool-calling.",
        "likely_cause": "PAYLOAD_TIMEOUT: Oversized batch payload.",
        "suggested_next_step": "Scale workers and inspect batch window.",
        "confidence": 0.95,
        "evidence": ["High payload latency observed in telemetry."],
        "runbook_references": ["payload_timeout_guide.md"]
    })
    choice2 = MagicMock(message=msg2)
    resp2 = MagicMock(choices=[choice2])

    mock_client.chat.completions.create.side_effect = [resp1, resp2]

    with patch("app.config.settings.OPENAI_API_KEY", "sk-mock-valid-key-for-test-12345"), \
         patch("openai.OpenAI", return_value=mock_client):
        res = triage_incident("INC-2026-1001", db_path=triage_db)
        assert res.incident_id == "INC-2026-1001"
        assert res.analysis_mode == "llm_tool_calling"
        assert res.confidence == 0.95
        assert res.requires_human_review is True
        assert "PAYLOAD_TIMEOUT" in res.likely_cause
        assert mock_client.chat.completions.create.call_count == 2

