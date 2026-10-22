"""
Customer-Experience Reliability KPIs for SyncOps Assistant.
All metrics are computed over synthetic datasets for educational SRE analysis.
Zero denominators and missing data are safely guarded with descriptive metadata.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import sqlite3

def calculate_sync_success_rate(success_count: int, total_count: int) -> dict[str, Any]:
    """
    KPI 1: Sync Success Rate
    Numerator: Count of successful sync events
    Denominator: Total sync attempts
    Units: Percentage (%)
    """
    rate = round((success_count / total_count * 100.0), 2) if total_count > 0 else 0.0
    return {
        "name": "Sync Success Rate",
        "value": rate,
        "unit": "%",
        "numerator": success_count,
        "denominator": total_count,
        "sample_size": total_count,
        "description": "Percentage of sync attempts that completed successfully without error."
    }

def calculate_recovery_rate(recovered_count: int, total_incidents: int) -> dict[str, Any]:
    """
    KPI 2: Recovery Rate
    Numerator: Count of incidents with status MITIGATED or RESOLVED
    Denominator: Total count of incidents
    Units: Percentage (%)
    """
    rate = round((recovered_count / total_incidents * 100.0), 2) if total_incidents > 0 else 0.0
    return {
        "name": "Recovery Rate",
        "value": rate,
        "unit": "%",
        "numerator": recovered_count,
        "denominator": total_incidents,
        "sample_size": total_incidents,
        "description": "Percentage of detected incidents successfully mitigated or resolved."
    }

def calculate_time_to_recover(total_duration_minutes: float, resolved_incident_count: int) -> dict[str, Any]:
    """
    KPI 3: Time to Recover (MTTR)
    Numerator: Total recovery duration across resolved incidents (minutes)
    Denominator: Count of resolved incidents with recorded recovery time
    Units: Minutes
    """
    mttr = round((total_duration_minutes / resolved_incident_count), 2) if resolved_incident_count > 0 else 0.0
    return {
        "name": "Time to Recover (MTTR)",
        "value": mttr,
        "unit": "minutes",
        "numerator_minutes": total_duration_minutes,
        "denominator_count": resolved_incident_count,
        "sample_size": resolved_incident_count,
        "description": "Mean time elapsed between incident detection and confirmed recovery."
    }

def calculate_repeat_failure_rate(customers_with_repeat_failures: int, customers_with_any_failure: int) -> dict[str, Any]:
    """
    KPI 4: Repeat Failure Rate
    Numerator: Customers experiencing more than 1 sync failure in window
    Denominator: Customers experiencing at least 1 sync failure in window
    Units: Percentage (%)
    """
    rate = round((customers_with_repeat_failures / customers_with_any_failure * 100.0), 2) if customers_with_any_failure > 0 else 0.0
    return {
        "name": "Repeat Failure Rate",
        "value": rate,
        "unit": "%",
        "numerator": customers_with_repeat_failures,
        "denominator": customers_with_any_failure,
        "sample_size": customers_with_any_failure,
        "description": "Percentage of impacted customers who experienced recurring sync failures."
    }

def calculate_sync_related_support_tickets(ticket_count: int, total_failures: int) -> dict[str, Any]:
    """
    KPI 5: Sync-Related Support Tickets
    Measurement: Volume of customer support tickets tagged with sync issues.
    Secondary metric: Ticket-to-failure conversion ratio.
    Units: Count (and % ratio)
    """
    conversion_ratio = round((ticket_count / total_failures * 100.0), 2) if total_failures > 0 else 0.0
    return {
        "name": "Sync-Related Support Tickets",
        "value": ticket_count,
        "unit": "tickets",
        "total_failures": total_failures,
        "ticket_to_failure_ratio": conversion_ratio,
        "sample_size": ticket_count,
        "description": "Customer support escalation volume and ticket-to-failure conversion ratio."
    }

def calculate_self_service_resolution_rate(self_service_count: int, total_tickets: int) -> dict[str, Any]:
    """
    KPI 6: Self-Service Resolution Rate
    Numerator: Support tickets resolved via self-service troubleshooting
    Denominator: Total support tickets
    Units: Percentage (%)
    """
    rate = round((self_service_count / total_tickets * 100.0), 2) if total_tickets > 0 else 0.0
    return {
        "name": "Self-Service Resolution Rate",
        "value": rate,
        "unit": "%",
        "numerator": self_service_count,
        "denominator": total_tickets,
        "sample_size": total_tickets,
        "description": "Percentage of support tickets resolved through in-app guided self-service."
    }

def calculate_adoption_rate(adopted_users: int, daily_active_users: int, total_registered_users: int = 0) -> dict[str, Any]:
    """
    KPI 7: Adoption Rate
    Numerator: Users actively utilizing sync features
    Denominator: Total Daily Active Users (DAU)
    Units: Percentage (%)
    """
    rate = round((adopted_users / daily_active_users * 100.0), 2) if daily_active_users > 0 else 0.0
    return {
        "name": "Adoption Rate",
        "value": rate,
        "unit": "%",
        "numerator": adopted_users,
        "denominator": daily_active_users,
        "total_registered_users": total_registered_users,
        "sample_size": daily_active_users,
        "description": "Percentage of daily active users who have enabled and actively sync telemetry."
    }

def compute_all_kpis(conn: sqlite3.Connection, window_hours: int | None = None) -> dict[str, Any]:
    """
    Queries SQLite database and computes all 7 customer-experience KPIs.
    If window_hours is provided, filters time-bounded events to that window.
    """
    now = datetime.now(timezone.utc)
    time_filter_sync = ""
    params_sync: list[Any] = []
    time_filter_inc = ""
    params_inc: list[Any] = []
    time_filter_tck = ""
    params_tck: list[Any] = []

    if window_hours is not None:
        cutoff = (now - timedelta(hours=window_hours)).isoformat()
        time_filter_sync = "WHERE timestamp >= ?"
        params_sync = [cutoff]
        time_filter_inc = "WHERE start_time >= ?"
        params_inc = [cutoff]
        time_filter_tck = "WHERE timestamp >= ?"
        params_tck = [cutoff]

    # 1. Sync Success Rate & Total Failures
    cur = conn.execute(
        f"""SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN status = 'FAILURE' THEN 1 ELSE 0 END) as failures
            FROM sync_events {time_filter_sync}""",
        params_sync
    )
    sync_row = cur.fetchone()
    total_syncs = sync_row["total"] or 0
    success_syncs = sync_row["successes"] or 0
    failure_syncs = sync_row["failures"] or 0
    kpi1 = calculate_sync_success_rate(success_syncs, total_syncs)

    # 2. Recovery Rate & 3. MTTR
    cur = conn.execute(
        f"""SELECT id, status, start_time, recovery_time 
            FROM incidents {time_filter_inc}""",
        params_inc
    )
    incidents = cur.fetchall()
    total_incidents = len(incidents)
    recovered_count = sum(1 for inc in incidents if inc["status"] in ("MITIGATED", "RESOLVED"))
    kpi2 = calculate_recovery_rate(recovered_count, total_incidents)

    total_duration_minutes = 0.0
    resolved_with_time = 0
    for inc in incidents:
        if inc["recovery_time"] and inc["start_time"]:
            try:
                st = datetime.fromisoformat(inc["start_time"])
                rt = datetime.fromisoformat(inc["recovery_time"])
                duration = max(0.0, (rt - st).total_seconds() / 60.0)
                total_duration_minutes += duration
                resolved_with_time += 1
            except Exception:
                pass
    kpi3 = calculate_time_to_recover(total_duration_minutes, resolved_with_time)

    # 4. Repeat Failure Rate
    cur = conn.execute(
        f"""SELECT customer_id, COUNT(*) as fail_count 
            FROM sync_events 
            {time_filter_sync + (' AND' if time_filter_sync else 'WHERE')} status = 'FAILURE' 
            GROUP BY customer_id""",
        params_sync
    )
    customer_fails = cur.fetchall()
    customers_with_any_failure = len(customer_fails)
    customers_with_repeat_failures = sum(1 for row in customer_fails if row["fail_count"] > 1)
    kpi4 = calculate_repeat_failure_rate(customers_with_repeat_failures, customers_with_any_failure)

    # 5. Sync-Related Support Tickets & 6. Self-Service Resolution Rate
    cur = conn.execute(
        f"""SELECT 
            COUNT(*) as total_tickets,
            SUM(CASE WHEN resolved_via_self_service = 1 THEN 1 ELSE 0 END) as self_service
            FROM support_tickets {time_filter_tck}""",
        params_tck
    )
    tck_row = cur.fetchone()
    total_tickets = tck_row["total_tickets"] or 0
    self_service_tickets = tck_row["self_service"] or 0
    kpi5 = calculate_sync_related_support_tickets(total_tickets, failure_syncs)
    kpi6 = calculate_self_service_resolution_rate(self_service_tickets, total_tickets)

    # 7. Adoption Rate (Latest record from adoption_records)
    cur = conn.execute(
        "SELECT daily_active_users, total_registered_users, sync_feature_adopted_users, date FROM adoption_records ORDER BY date DESC LIMIT 1"
    )
    adopt_row = cur.fetchone()
    if adopt_row:
        kpi7 = calculate_adoption_rate(
            adopt_row["sync_feature_adopted_users"],
            adopt_row["daily_active_users"],
            adopt_row["total_registered_users"]
        )
        kpi7["latest_date"] = adopt_row["date"]
    else:
        kpi7 = calculate_adoption_rate(0, 0, 0)
        kpi7["latest_date"] = None

    return {
        "sync_success_rate": kpi1,
        "recovery_rate": kpi2,
        "time_to_recover": kpi3,
        "repeat_failure_rate": kpi4,
        "sync_related_support_tickets": kpi5,
        "self_service_resolution_rate": kpi6,
        "adoption_rate": kpi7,
        "window_hours": window_hours,
        "calculated_at": now.isoformat(),
        "disclosure": "SYNTHETIC_DATA_ONLY"
    }
