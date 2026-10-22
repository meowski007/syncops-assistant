"""
Deterministic Rule-Based Triage Engine for SyncOps Assistant.
Provides fully offline, reproducible, zero-credential incident investigation.
Executes the same tool interfaces to correlate telemetry with Markdown runbooks.
"""

from pathlib import Path
from typing import Any
from app.schemas import TriageResult
from app.triage.tools import tool_get_incident_details, tool_search_and_read_runbook
from app.logging_config import logger

RUNBOOK_MAP = {
    "PAYLOAD_TIMEOUT": "payload_timeout_guide.md",
    "RATE_LIMITED": "payload_timeout_guide.md",
    "AUTH_EXPIRED": "authentication_errors.md",
    "FIRMWARE_UNSUPPORTED": "firmware_update_failures.md",
    "SCHEMA_MISMATCH": "sync_failures.md",
    "DATABASE_LOCK": "sync_failures.md",
}

RECOMMENDED_ACTIONS = {
    "PAYLOAD_TIMEOUT": "Scale ingestion decompression workers and increase gateway client timeout buffer to 10s. Apply exponential jitter to client retry policies.",
    "RATE_LIMITED": "Inspect upstream tenant batch sync volume. Adjust token-bucket refill rate or partition batch window.",
    "AUTH_EXPIRED": "Trigger JWKS key cache refresh on ingress proxies and verify identity provider leaf certificate rotation intermediate chain.",
    "FIRMWARE_UNSUPPORTED": "Halt automated OTA firmware staging. Reduce gateway BLE transmission chunk size to 128 bytes to avoid device buffer truncation.",
    "SCHEMA_MISMATCH": "Redeploy edge gateway schema compatibility layer to accept deprecated optional fields from legacy client builds.",
    "DATABASE_LOCK": "Inspect slow database shard write transactions and terminate blocking locks exceeding 2,500ms.",
}

def run_deterministic_triage(incident_id: str, db_path: str | Path | None = None) -> TriageResult:
    """
    Executes deterministic SRE triage by inspecting database telemetry
    and correlating findings with official Markdown runbooks.
    """
    logger.info(f"Executing deterministic triage fallback for incident: {incident_id}")
    
    # 1. Fetch incident details using the tool
    incident_data = tool_get_incident_details(incident_id, db_path=db_path)
    
    if "error" in incident_data or incident_data.get("status") == "NOT_FOUND":
        return TriageResult(
            incident_id=incident_id,
            summary=f"Incident {incident_id} not found in database.",
            likely_cause="Incident identifier does not correspond to an existing record.",
            suggested_next_step="Verify the incident ID and check the /incidents list for active incidents.",
            confidence=0.1,
            evidence=["Database lookup returned no matching incident record."],
            runbook_references=[],
            requires_human_review=True,
            analysis_mode="deterministic_fallback"
        )
        
    title = incident_data.get("title", "Unknown Incident")
    severity = incident_data.get("severity", "SEV3")
    status = incident_data.get("status", "DETECTED")
    cohort = incident_data.get("affected_cohort", "Unknown")
    category = incident_data.get("failure_category", "UNKNOWN")
    root_cause = incident_data.get("root_cause_summary") or "No root cause documented yet."
    
    # 2. Correlate with Runbook using the tool
    target_runbook = RUNBOOK_MAP.get(category, "sync_failures.md")
    runbook_res = tool_search_and_read_runbook(target_runbook)
    
    runbook_refs = [target_runbook, "recovery_confirmation.md"]
    
    # 3. Compile empirical telemetry evidence
    evidence = []
    cohort_stats = incident_data.get("cohort_telemetry", {})
    if cohort_stats:
        total = cohort_stats.get("total_events_sampled", 0)
        fails = cohort_stats.get("failure_events_sampled", 0)
        avg_lat = cohort_stats.get("avg_latency_ms", 0.0)
        fail_pct = round((fails / total * 100.0), 1) if total > 0 else 0.0
        evidence.append(
            f"Cohort '{cohort}' telemetry: {fails}/{total} sync failures sampled ({fail_pct}% failure rate, avg latency {avg_lat}ms)."
        )
        
    tickets = incident_data.get("associated_tickets", [])
    if tickets:
        evidence.append(f"Customer impact confirmed: {len(tickets)} associated support tickets filed.")
    else:
        evidence.append("No customer support tickets directly linked at detection time.")
        
    evidence.append(f"Root cause telemetry: {root_cause}")
    
    # 4. Formulate actionable recommendation based on runbook and category
    suggested_step = RECOMMENDED_ACTIONS.get(
        category,
        f"Refer to {target_runbook} to initiate standard diagnostic checklist and verify metric stability before resolving."
    )
    
    summary = f"[{severity} - {status}] {title}. Impact localized to cohort '{cohort}' due to {category}."
    likely_cause = f"{category}: {root_cause}"
    confidence = 0.92 if category in RUNBOOK_MAP else 0.65
    
    return TriageResult(
        incident_id=incident_id,
        summary=summary,
        likely_cause=likely_cause,
        suggested_next_step=suggested_step,
        confidence=confidence,
        evidence=evidence,
        runbook_references=runbook_refs,
        requires_human_review=True,
        analysis_mode="deterministic_fallback"
    )
