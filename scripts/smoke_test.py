"""
End-to-End Smoke Test Script for SyncOps Assistant.
Can verify live HTTP services or run in-process verification across all platform layers.
"""

import sys
from pathlib import Path
import requests

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import check_db_health, get_db_path
from app.triage.agent import triage_incident
from app.slack.mock import MockSlackClient

API_BASE_URL = "http://127.0.0.1:8000"

def log_test(name: str, passed: bool, detail: str = ""):
    symbol = "[PASS]" if passed else "[FAIL]"
    print(f"{symbol} {name} {f'({detail})' if detail else ''}")
    if not passed:
        sys.exit(1)

def run_smoke_tests():
    print("=" * 65)
    print("SYNCOPS ASSISTANT: END-TO-END SMOKE TEST")
    print("=" * 65)

    # 1. Database Check
    print("\n--- 1. Database Layer ---")
    health = check_db_health()
    db_ok = health.get("connected") and health.get("record_counts", {}).get("customers", 0) > 0
    log_test("Database Connectivity & Record Integrity", db_ok, f"Counts: {health.get('record_counts')}")

    # 2. Triage Fallback Engine
    print("\n--- 2. Autonomous SRE Triage Engine (Offline Fallback) ---")
    triage_res = triage_incident("INC-2026-1001", force_fallback=True)
    triage_ok = (
        triage_res.incident_id == "INC-2026-1001" and
        triage_res.analysis_mode == "deterministic_fallback" and
        len(triage_res.evidence) > 0 and
        len(triage_res.runbook_references) > 0
    )
    log_test("Triage Investigation Schema & Runbook Binding", triage_ok, f"Likely Cause: {triage_res.likely_cause}")

    # 3. Slack Mock Runner
    print("\n--- 3. Local Mock Slack Layer ---")
    mock_slack = MockSlackClient()
    cmd_res = mock_slack.execute_slash_command("/syncstatus")
    slack_ok = cmd_res.get("mode") == "SIMULATED_SLACK_MOCK" and len(cmd_res.get("blocks", [])) > 0
    log_test("Mock Slash Command /syncstatus", slack_ok, f"Blocks: {len(cmd_res.get('blocks', []))}")

    mention_res = mock_slack.simulate_app_mention("@SyncOps triage INC-2026-1001")
    mention_ok = "Triage Assessment" in mention_res.get("response_text", "")
    log_test("Mock App Mention SRE Triage Trigger", mention_ok)

    # 4. Live REST API Check (if server is running)
    print("\n--- 4. REST API Endpoints ---")
    try:
        r_health = requests.get(f"{API_BASE_URL}/health", timeout=1.5)
        live_api = (r_health.status_code == 200)
    except requests.exceptions.RequestException:
        live_api = False

    if live_api:
        print(f"Detected live FastAPI server at {API_BASE_URL}:")
        
        # Health
        log_test("Live GET /health", True, f"Status: {r_health.json()['status']}")
        
        # KPIs
        r_kpis = requests.get(f"{API_BASE_URL}/kpis")
        log_test("Live GET /kpis", r_kpis.status_code == 200, f"Sync Success: {r_kpis.json()['sync_success_rate']['value']}%")
        
        # Incidents
        r_incs = requests.get(f"{API_BASE_URL}/incidents?limit=5")
        log_test("Live GET /incidents", r_incs.status_code == 200, f"Returned: {len(r_incs.json())} incidents")

        # Metrics
        r_met = requests.get(f"{API_BASE_URL}/metrics")
        log_test("Live GET /metrics", r_met.status_code == 200 and "syncops_http_requests_total" in r_met.text)

        # Post Triage
        r_tri = requests.post(f"{API_BASE_URL}/triage", json={"incident_id": "INC-2026-1001", "force_fallback": True})
        log_test("Live POST /triage", r_tri.status_code == 200 and r_tri.json()["analysis_mode"] == "deterministic_fallback")
    else:
        print(f"Note: Live API server is not running on {API_BASE_URL}. Running in-process FastAPI TestClient verification:")
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as client:
            r1 = client.get("/health")
            log_test("In-Process GET /health", r1.status_code == 200)
            r2 = client.get("/kpis")
            log_test("In-Process GET /kpis", r2.status_code == 200)
            r3 = client.get("/incidents")
            log_test("In-Process GET /incidents", r3.status_code == 200)
            r4 = client.get("/metrics")
            log_test("In-Process GET /metrics", r4.status_code == 200 and "syncops_http_requests_total" in r4.text)

    print("\n" + "=" * 65)
    print("ALL SMOKE TESTS PASSED CLEANLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_smoke_tests()
