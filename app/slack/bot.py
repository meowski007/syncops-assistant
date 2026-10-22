"""
Slack Bolt Application for SyncOps Assistant.
Provides production Slack Bolt handlers with Socket Mode support.
Gracefully handles missing credentials with informative diagnostics.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Any
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from app.config import settings
from app.database import get_db, get_db_path
from app.kpis import compute_all_kpis
from app.incidents import list_incidents
from app.triage.agent import triage_incident
from app.logging_config import logger

# Global in-memory alert state for cooldown enforcement
_last_alert_time: datetime | None = None

def get_slack_app() -> App | None:
    """Initializes and returns the Slack Bolt App if bot token and signing secret are configured."""
    bot_token = settings.SLACK_BOT_TOKEN or os.environ.get("SLACK_BOT_TOKEN")
    signing_secret = settings.SLACK_SIGNING_SECRET or os.environ.get("SLACK_SIGNING_SECRET")

    if not bot_token or not signing_secret or "placeholder" in bot_token:
        logger.warning("Slack credentials not configured or using placeholders. Real Slack bot disabled.")
        return None

    app = App(token=bot_token, signing_secret=signing_secret)
    register_handlers(app)
    return app

def format_sync_status_blocks(kpis: dict[str, Any]) -> list[dict[str, Any]]:
    """Formats 7 KPIs into Slack Block Kit structure."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📊 SyncOps Platform Reliability Status", "emoji": True}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*[SYNTHETIC TELEMETRY]* Customer-Experience Metrics (Last 24h Window):\n"
                        f"• *Sync Success Rate:* `{kpis['sync_success_rate']['value']}%` (Sample: {kpis['sync_success_rate']['sample_size']})\n"
                        f"• *Recovery Rate:* `{kpis['recovery_rate']['value']}%` ({kpis['recovery_rate']['numerator']}/{kpis['recovery_rate']['denominator']} incidents)\n"
                        f"• *MTTR:* `{kpis['time_to_recover']['value']} mins`\n"
                        f"• *Repeat Failure Rate:* `{kpis['repeat_failure_rate']['value']}%`\n"
                        f"• *Support Tickets:* `{kpis['sync_related_support_tickets']['value']}` (Ratio: {kpis['sync_related_support_tickets']['ticket_to_failure_ratio']}%)\n"
                        f"• *Self-Service Resolution:* `{kpis['self_service_resolution_rate']['value']}%`\n"
                        f"• *Sync Feature Adoption:* `{kpis['adoption_rate']['value']}%`"
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Calculated at: {kpis['calculated_at']} | Source: SyncOps Synthetic Store"}
            ]
        }
    ]

def format_incidents_blocks(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Formats incident list into Slack Block Kit structure."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚨 SyncOps Active & Open Incidents", "emoji": True}
        }
    ]
    if not incidents:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "✅ *All systems nominal.* No open or investigating incidents."}
        })
        return blocks

    for inc in incidents[:5]:
        sev_emoji = "🔴" if inc["severity"] == "SEV1" else "🟠" if inc["severity"] == "SEV2" else "🟡"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{sev_emoji} *{inc['id']}* - `{inc['severity']}` [{inc['status']}]\n"
                        f"*{inc['title']}*\n"
                        f"• Cohort: `{inc['affected_cohort']}` | Failure: `{inc['failure_category']}`\n"
                        f"• Started: {inc['start_time']}"
            }
        })
    return blocks

def register_handlers(app: App) -> None:
    """Registers slash commands, app mentions, and event handlers on the Bolt app."""

    @app.command("/syncstatus")
    def handle_syncstatus(ack, respond):
        ack()
        with get_db() as conn:
            kpis = compute_all_kpis(conn, window_hours=24)
        blocks = format_sync_status_blocks(kpis)
        respond(blocks=blocks)

    @app.command("/incidents")
    def handle_incidents(ack, respond):
        ack()
        with get_db() as conn:
            open_incs = list_incidents(conn, status="INVESTIGATING", limit=10)
            if not open_incs:
                open_incs = list_incidents(conn, limit=5)
        blocks = format_incidents_blocks(open_incs)
        respond(blocks=blocks)

    @app.event("app_mention")
    def handle_mention(event, say):
        text = event.get("text", "")
        # Triage inquiry: e.g. "@SyncOps triage INC-2026-1001"
        if "triage" in text.lower():
            words = text.split()
            inc_id = next((w for w in words if w.startswith("INC-")), "INC-2026-1001")
            res = triage_incident(inc_id)
            say(
                f"📋 *Triage Assessment for {inc_id}* [{res.analysis_mode}]\n"
                f"• *Summary:* {res.summary}\n"
                f"• *Likely Cause:* {res.likely_cause}\n"
                f"• *Suggested Next Step:* {res.suggested_next_step}\n"
                f"• *Confidence:* {int(res.confidence * 100)}%\n"
                f"• *Runbook:* `{', '.join(res.runbook_references)}`"
            )
        else:
            with get_db() as conn:
                kpis = compute_all_kpis(conn, window_hours=24)
            rate = kpis["sync_success_rate"]["value"]
            say(f"👋 Hi! Current synthetic sync success rate is *{rate}%*. Type `/syncstatus` for full KPI telemetry or mention me with `triage <INC_ID>` to investigate an incident.")

def reset_alert_cooldown() -> None:
    """Resets the alert cooldown timer (primarily used for test isolation)."""
    global _last_alert_time
    _last_alert_time = None

def check_and_send_threshold_alert(
    app: App | None = None,
    failure_rate_threshold: float = 0.05,
    cooldown_minutes: int = 15,
    window_hours: int | None = 24,
    db_path: str | None = None
) -> dict[str, Any]:
    """
    Evaluates sync failure rate. If it exceeds threshold and cooldown has passed,
    dispatches an alert. Returns status dictionary.
    """
    global _last_alert_time
    now = datetime.now(timezone.utc)

    with get_db(db_path) as conn:
        kpis = compute_all_kpis(conn, window_hours=window_hours)

    success_rate = kpis["sync_success_rate"]["value"]
    failure_rate = round((100.0 - success_rate) / 100.0, 4) if kpis["sync_success_rate"]["sample_size"] > 0 else 0.0

    in_cooldown = False
    if _last_alert_time:
        elapsed = (now - _last_alert_time).total_seconds() / 60.0
        if elapsed < cooldown_minutes:
            in_cooldown = True

    should_alert = (failure_rate >= failure_rate_threshold) and not in_cooldown

    result = {
        "failure_rate": failure_rate,
        "threshold": failure_rate_threshold,
        "in_cooldown": in_cooldown,
        "alert_triggered": should_alert,
        "timestamp": now.isoformat()
    }

    if should_alert:
        _last_alert_time = now
        alert_msg = (
            f"🚨 *[SYNTHETIC ALERT]* Sync failure rate at *{round(failure_rate * 100, 2)}%* "
            f"exceeded threshold of {round(failure_rate_threshold * 100, 2)}% over past 1 hour."
        )
        if app:
            try:
                app.client.chat_postMessage(channel=settings.SLACK_ALERT_CHANNEL, text=alert_msg)
                result["dispatched_to_slack"] = True
            except Exception as e:
                result["dispatched_to_slack"] = False
                result["error"] = str(e)
        else:
            result["dispatched_to_slack"] = False
            result["note"] = "Slack app not configured; simulated alert generated."

    return result

def start_slack_socket_mode():
    """Starts Slack Bolt in Socket Mode if tokens are provided."""
    app_token = settings.SLACK_APP_TOKEN or os.environ.get("SLACK_APP_TOKEN")
    app = get_slack_app()
    if not app or not app_token or "placeholder" in app_token:
        print("[SLACK] Real Slack credentials not set. Use 'python -m app.slack.mock' for local mock mode.")
        return
    handler = SocketModeHandler(app, app_token)
    print("[SLACK] Starting Slack Bolt Socket Mode listener...")
    handler.start()

if __name__ == "__main__":
    start_slack_socket_mode()
