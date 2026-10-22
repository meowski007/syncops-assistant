"""
Local Zero-Credential Mock Runner for Slack Bot.
Simulates Slack Bolt slash commands, app mentions, and threshold alerts
without requiring a Slack account, API token, or external network access.
ALL OUTPUT IS SIMULATED AND CLEARLY LABELED AS SYNTHETIC.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import get_db, get_db_path
from app.kpis import compute_all_kpis
from app.incidents import list_incidents
from app.triage.agent import triage_incident
from app.slack.bot import (
    format_sync_status_blocks,
    format_incidents_blocks,
    check_and_send_threshold_alert,
)

class MockSlackClient:
    """Simulates Slack interactive events and slash commands locally."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path

    def execute_slash_command(self, command: str, text: str = "") -> dict[str, Any]:
        """Simulates incoming slash command invocation."""
        clean_cmd = command.strip().lower()
        
        if clean_cmd == "/syncstatus":
            with get_db(self.db_path) as conn:
                kpis = compute_all_kpis(conn, window_hours=24)
            blocks = format_sync_status_blocks(kpis)
            return {
                "command": "/syncstatus",
                "mode": "SIMULATED_SLACK_MOCK",
                "blocks": blocks,
                "text": f"[SIMULATED SLACK] Sync Success Rate: {kpis['sync_success_rate']['value']}%",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        elif clean_cmd == "/incidents":
            with get_db(self.db_path) as conn:
                open_incs = list_incidents(conn, status="INVESTIGATING", limit=5)
                if not open_incs:
                    open_incs = list_incidents(conn, limit=5)
            blocks = format_incidents_blocks(open_incs)
            return {
                "command": "/incidents",
                "mode": "SIMULATED_SLACK_MOCK",
                "blocks": blocks,
                "incident_count": len(open_incs),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "command": command,
                "mode": "SIMULATED_SLACK_MOCK",
                "error": f"Unknown mock slash command '{command}'. Available: /syncstatus, /incidents",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def simulate_app_mention(self, message: str) -> dict[str, Any]:
        """Simulates an @SyncOps app mention in a Slack channel."""
        text = message.strip()
        if "triage" in text.lower():
            words = text.split()
            inc_id = next((w for w in words if w.startswith("INC-")), "INC-2026-1001")
            triage_res = triage_incident(inc_id, force_fallback=True, db_path=self.db_path)
            response_text = (
                f"[SIMULATED SLACK] 📋 Triage Assessment for {inc_id} ({triage_res.analysis_mode}):\n"
                f"• Summary: {triage_res.summary}\n"
                f"• Likely Cause: {triage_res.likely_cause}\n"
                f"• Next Step: {triage_res.suggested_next_step}\n"
                f"• Confidence: {int(triage_res.confidence * 100)}%\n"
                f"• Runbooks: {', '.join(triage_res.runbook_references)}"
            )
            return {
                "mention": message,
                "mode": "SIMULATED_SLACK_MOCK",
                "triage_result": triage_res.model_dump(),
                "response_text": response_text
            }
        else:
            with get_db(self.db_path) as conn:
                kpis = compute_all_kpis(conn, window_hours=24)
            rate = kpis["sync_success_rate"]["value"]
            response_text = (
                f"[SIMULATED SLACK] 👋 Hi! Current synthetic sync success rate is {rate}%. "
                f"Run /syncstatus for full KPI metrics or mention me with 'triage <INC_ID>'."
            )
            return {
                "mention": message,
                "mode": "SIMULATED_SLACK_MOCK",
                "response_text": response_text,
                "sync_success_rate": rate
            }

    def trigger_threshold_check(
        self,
        threshold: float = 0.05,
        cooldown_minutes: int = 15,
        window_hours: int | None = 24
    ) -> dict[str, Any]:
        """Simulates threshold monitoring and alert generation."""
        res = check_and_send_threshold_alert(
            app=None,
            failure_rate_threshold=threshold,
            cooldown_minutes=cooldown_minutes,
            window_hours=window_hours,
            db_path=self.db_path
        )
        res["mode"] = "SIMULATED_SLACK_MOCK"
        return res

def run_interactive_mock_demo():
    """Runs a complete visual demonstration of the mock Slack bot in CLI."""
    client = MockSlackClient()
    
    print("=" * 70)
    print("🤖 SYNCOPS ASSISTANT: LOCAL SLACK MOCK RUNNER (NO CREDENTIALS REQUIRED)")
    print("DISCLOSURE: 100% Simulated locally. No connection to Slack servers.")
    print("=" * 70)

    print("\n--- [1] Simulating Slash Command: /syncstatus ---")
    status_res = client.execute_slash_command("/syncstatus")
    print(status_res["text"])
    for block in status_res["blocks"]:
        if block.get("type") == "section":
            print(block["text"]["text"])

    print("\n--- [2] Simulating Slash Command: /incidents ---")
    inc_res = client.execute_slash_command("/incidents")
    for block in inc_res["blocks"]:
        if "text" in block:
            t = block["text"].get("text", "")
            print(t)

    print("\n--- [3] Simulating App Mention: '@SyncOps triage INC-2026-1001' ---")
    mention_res = client.simulate_app_mention("@SyncOps triage INC-2026-1001")
    print(mention_res["response_text"])

    print("\n--- [4] Simulating Threshold Alert Check (Threshold = 0.03) ---")
    alert_res = client.trigger_threshold_check(threshold=0.03, cooldown_minutes=15)
    print(f"Triggered: {alert_res['alert_triggered']} | Failure Rate: {round(alert_res['failure_rate'] * 100, 2)}% | Threshold: {alert_res['threshold'] * 100}% | In Cooldown: {alert_res['in_cooldown']}")

    print("\n" + "=" * 70)
    print("✅ Slack mock demo complete. Fully verified locally without external tokens.")
    print("=" * 70)

if __name__ == "__main__":
    run_interactive_mock_demo()
