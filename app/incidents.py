"""
Incident Management and Query Services for SyncOps Assistant.
Provides parameterized filtering and cohort telemetry correlation for SRE triage.
"""

from typing import Any
import sqlite3

def list_incidents(
    conn: sqlite3.Connection,
    status: str | None = None,
    severity: str | None = None,
    cohort: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Lists incidents with validated query filters."""
    query = "SELECT id, title, severity, status, start_time, recovery_time, affected_cohort, failure_category, root_cause_summary FROM incidents WHERE 1=1"
    params: list[Any] = []

    if status:
        query += " AND status = ?"
        params.append(status.upper())
    if severity:
        query += " AND severity = ?"
        params.append(severity.upper())
    if cohort:
        query += " AND affected_cohort = ?"
        params.append(cohort)

    query += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

def get_incident_by_id(conn: sqlite3.Connection, incident_id: str) -> dict[str, Any] | None:
    """Retrieves a single incident by ID with correlated telemetry statistics."""
    cursor = conn.execute(
        "SELECT id, title, severity, status, start_time, recovery_time, affected_cohort, failure_category, root_cause_summary FROM incidents WHERE id = ?",
        (incident_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None

    inc = dict(row)

    # Correlate failure metrics for the affected cohort
    cohort_stats = conn.execute(
        """SELECT 
            COUNT(*) as total_events,
            SUM(CASE WHEN status = 'FAILURE' THEN 1 ELSE 0 END) as failure_events,
            AVG(latency_ms) as avg_latency_ms
           FROM sync_events 
           WHERE customer_id IN (SELECT id FROM customers WHERE cohort = ?)
        """,
        (inc["affected_cohort"],)
    ).fetchone()

    inc["cohort_telemetry"] = {
        "cohort": inc["affected_cohort"],
        "total_events_sampled": cohort_stats["total_events"] or 0,
        "failure_events_sampled": cohort_stats["failure_events"] or 0,
        "avg_latency_ms": round(cohort_stats["avg_latency_ms"] or 0.0, 2),
    }

    # Fetch any associated support tickets
    tickets = conn.execute(
        "SELECT id, customer_id, timestamp, category, resolved_via_self_service FROM support_tickets WHERE incident_id = ? LIMIT 10",
        (incident_id,)
    ).fetchall()
    inc["associated_tickets"] = [dict(t) for t in tickets]

    return inc
