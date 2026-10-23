"""Data Quality Reporting module for SyncOps ETL pipeline."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.config import config
from pipeline.validate import ValidationReportSummary
from app.logging_config import logger

DQ_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS data_quality_reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    total_records INTEGER NOT NULL,
    accepted_records INTEGER NOT NULL,
    rejected_records INTEGER NOT NULL,
    warning_count INTEGER NOT NULL,
    rejection_breakdown_json TEXT NOT NULL,
    warning_breakdown_json TEXT NOT NULL,
    report_markdown_path TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dq_run_id ON data_quality_reports(run_id);
"""

def init_dq_schema(db_path: Path | str | None = None) -> None:
    """Initializes table for data quality report tracking."""
    target_path = Path(db_path) if db_path else config.db_path
    conn = sqlite3.connect(str(target_path))
    try:
        conn.executescript(DQ_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

def generate_quality_markdown_report(
    run_id: str,
    source_desc: str,
    summary: ValidationReportSummary,
    load_stats: dict[str, Any],
    reports_dir: Path | str | None = None
) -> Path:
    """Generates a comprehensive Markdown audit report for the ETL run."""
    target_dir = Path(reports_dir) if reports_dir else config.reports_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = target_dir / f"dq_report_{run_id}.md"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    overall_status = "PASSED" if summary.rejected_records == 0 and summary.warning_count == 0 else "WARNING" if summary.rejected_records == 0 else "FAILED"
    status_badge = "🟢 PASSED" if overall_status == "PASSED" else "🟡 WARNINGS DETECTED" if overall_status == "WARNING" else "🔴 BLOCKING REJECTIONS DETECTED"
    
    rejection_rows = ""
    if summary.rejection_breakdown:
        for reason, count in summary.rejection_breakdown.items():
            rejection_rows += f"| `{reason}` | {count} | BLOCKING |\n"
    else:
        rejection_rows = "| *None* | 0 | N/A |\n"

    warning_rows = ""
    if summary.warning_breakdown:
        for warn, count in summary.warning_breakdown.items():
            warning_rows += f"| `{warn}` | {count} | NON-BLOCKING |\n"
    else:
        warning_rows = "| *None* | 0 | N/A |\n"

    md_content = f"""# SyncOps Data Quality & Governance Audit Report

> **DISCLOSURE:** All telemetry analyzed in this run is strictly synthetic for educational reliability engineering.

---

### Run Executive Summary
- **Pipeline Run ID:** `{run_id}`
- **Source Ingested:** `{source_desc}`
- **Generated At:** `{now_str}`
- **Overall Data Quality Status:** **{status_badge}**
- **Idempotent Storage Mode:** `{'DRY RUN' if load_stats.get('dry_run') else 'LIVE SQLite PERSISTENCE'}`

---

### Row Count Reconciliation
| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Total Rows Extracted** | {summary.total_records} | 100.0% |
| **Accepted Records (Clean Layer)** | {summary.accepted_records} | {round(summary.accepted_records / max(1, summary.total_records) * 100, 2)}% |
| **Rejected Records (Dead-Letter Staging)** | {summary.rejected_records} | {round(summary.rejected_records / max(1, summary.total_records) * 100, 2)}% |
| **New Clean Records Inserted** | {load_stats.get('inserted', 0)} | — |
| **Duplicate Clean Records Skipped** | {load_stats.get('skipped_duplicates', 0)} | — |
| **Non-Blocking Warnings Logged** | {summary.warning_count} | — |

---

### Validation Catalog & Enforcement Rules
| Check Name | Type | Description |
| :--- | :--- | :--- |
| `required_columns` | **BLOCKING** | Enforces presence of id, customer_id, timestamp, status, latency_ms, payload_size_bytes. |
| `status_allowed_values` | **BLOCKING** | Enforces status in ('SUCCESS', 'FAILURE'). |
| `non_negative_metrics` | **BLOCKING** | Enforces latency_ms >= 0 and payload_size_bytes >= 0. |
| `timestamp_clock_skew` | **BLOCKING** | Flags timestamps exceeding +1h clock skew tolerance. |
| `latency_outlier_warning` | **WARNING** | Flags sync events exceeding 10,000ms. |
| `retry_outlier_warning` | **WARNING** | Flags sync attempts with retry_count > 5. |

---

### Rejection Reasons Breakdown
| Reason Code | Count | Severity |
| :--- | :--- | :--- |
{rejection_rows}

---

### Warnings Breakdown
| Warning Code | Count | Severity |
| :--- | :--- | :--- |
{warning_rows}

---

### Data Governance & Masking Verification
- **Customer Identifier Masking:** Active via HMAC-SHA256. Raw customer identifiers are quarantined to raw staging and never exposed in `clean_sync_events`.
- **Idempotency Guarantee:** Record fingerprints and primary keys prevent duplicate insertion across repeated executions.
"""

    report_path.write_text(md_content, encoding="utf-8")
    return report_path

def record_quality_report(
    run_id: str,
    source_desc: str,
    summary: ValidationReportSummary,
    load_stats: dict[str, Any],
    db_path: Path | str | None = None
) -> str:
    """Generates markdown report and writes metadata into SQLite data_quality_reports."""
    target_path = Path(db_path) if db_path else config.db_path
    init_dq_schema(target_path)
    
    report_file = generate_quality_markdown_report(run_id, source_desc, summary, load_stats)
    
    report_id = f"DQR-{uuid.uuid4().hex[:12]}"
    now_str = datetime.now(timezone.utc).isoformat()
    overall_status = "PASSED" if summary.rejected_records == 0 and summary.warning_count == 0 else "WARNING" if summary.rejected_records == 0 else "FAILED"
    
    conn = sqlite3.connect(str(target_path))
    try:
        conn.execute(
            """INSERT INTO data_quality_reports (
                report_id, run_id, created_at, status, total_records, accepted_records,
                rejected_records, warning_count, rejection_breakdown_json, warning_breakdown_json,
                report_markdown_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report_id,
                run_id,
                now_str,
                overall_status,
                summary.total_records,
                summary.accepted_records,
                summary.rejected_records,
                summary.warning_count,
                json.dumps(summary.rejection_breakdown),
                json.dumps(summary.warning_breakdown),
                str(report_file)
            )
        )
        conn.commit()
    finally:
        conn.close()
        
    logger.info(f"Data quality report saved: {report_id} at {report_file}")
    return report_id
