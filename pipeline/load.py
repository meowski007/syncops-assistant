"""Loading and Persistence module for SyncOps ETL pipeline."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.config import config
from app.logging_config import logger

PIPELINE_SCHEMA_SQL = """
-- Pipeline execution metadata tracking
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    finish_time TEXT,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    rows_extracted INTEGER NOT NULL DEFAULT 0,
    rows_accepted INTEGER NOT NULL DEFAULT 0,
    rows_rejected INTEGER NOT NULL DEFAULT 0,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    rows_updated INTEGER NOT NULL DEFAULT 0,
    rows_skipped_duplicates INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);

-- Raw staging layer: Preserves unmasked records for operational auditing
CREATE TABLE IF NOT EXISTS raw_sync_events (
    id TEXT,
    run_id TEXT NOT NULL,
    customer_id TEXT,
    timestamp TEXT,
    status TEXT,
    failure_category TEXT,
    latency_ms REAL,
    payload_size_bytes INTEGER,
    retry_count INTEGER,
    raw_json TEXT,
    ingested_at TEXT NOT NULL
);

-- Clean analytical layer: Validated, deduplicated, and PII-pseudonymized
CREATE TABLE IF NOT EXISTS clean_sync_events (
    id TEXT PRIMARY KEY,
    customer_id_masked TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    failure_category TEXT,
    latency_ms REAL NOT NULL,
    payload_size_bytes INTEGER NOT NULL,
    retry_count INTEGER NOT NULL,
    is_incident_window INTEGER NOT NULL DEFAULT 0,
    fingerprint TEXT NOT NULL,
    run_id TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

-- Rejected records dead-letter table
CREATE TABLE IF NOT EXISTS pipeline_rejected_records (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    record_identifier TEXT,
    raw_data TEXT,
    rejection_reason TEXT NOT NULL,
    rejected_at TEXT NOT NULL
);

-- Indexes for pipeline tables
CREATE INDEX IF NOT EXISTS idx_clean_sync_date ON clean_sync_events(date);
CREATE INDEX IF NOT EXISTS idx_clean_sync_status ON clean_sync_events(status);
CREATE INDEX IF NOT EXISTS idx_clean_sync_masked_cust ON clean_sync_events(customer_id_masked);
CREATE INDEX IF NOT EXISTS idx_clean_sync_fingerprint ON clean_sync_events(fingerprint);
CREATE INDEX IF NOT EXISTS idx_raw_sync_run_id ON raw_sync_events(run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_start ON pipeline_runs(start_time);
"""

def init_pipeline_schema(db_path: Path | str | None = None) -> None:
    """Initializes tables for pipeline metadata, raw staging, and clean analytical layers."""
    target_path = Path(db_path) if db_path else config.db_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    try:
        conn.executescript(PIPELINE_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

def load_pipeline_data(
    run_id: str,
    source_desc: str,
    raw_records: list[dict[str, Any]],
    clean_records: list[dict[str, Any]],
    rejected_records: list[dict[str, Any]],
    db_path: Path | str | None = None,
    dry_run: bool = False
) -> dict[str, int]:
    """
    Loads transformed clean records into clean_sync_events with transactional idempotency,
    stages raw records in raw_sync_events, and logs rejected records.
    
    Returns load stats dictionary.
    """
    target_path = Path(db_path) if db_path else config.db_path
    init_pipeline_schema(target_path)
    
    now_str = datetime.now(timezone.utc).isoformat()
    
    if dry_run:
        logger.info("DRY-RUN mode active: Skipping physical database writes.")
        return {
            "inserted": 0,
            "skipped_duplicates": 0,
            "raw_staged": len(raw_records),
            "rejected_logged": len(rejected_records),
            "dry_run": True
        }

    conn = sqlite3.connect(str(target_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        with conn:  # Transaction context manager
            # 1. Identify which clean records already exist (idempotency check)
            clean_ids = [c["id"] for c in clean_records]
            existing_ids: set[str] = set()
            
            # Query in chunks of 500 to stay within SQLite variable limits
            chunk_size = 500
            for i in range(0, len(clean_ids), chunk_size):
                chunk = clean_ids[i:i + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                cursor = conn.execute(f"SELECT id FROM clean_sync_events WHERE id IN ({placeholders})", chunk)
                for row in cursor.fetchall():
                    existing_ids.add(row["id"])

            records_to_insert = []
            skipped_duplicates = 0
            
            for item in clean_records:
                if item["id"] in existing_ids:
                    skipped_duplicates += 1
                else:
                    records_to_insert.append((
                        item["id"],
                        item["customer_id_masked"],
                        item["timestamp"],
                        item["date"],
                        item["status"],
                        item["failure_category"],
                        item["latency_ms"],
                        item["payload_size_bytes"],
                        item["retry_count"],
                        item["is_incident_window"],
                        item["fingerprint"],
                        run_id,
                        now_str
                    ))
                    existing_ids.add(item["id"])

            # 2. Insert new clean records
            if records_to_insert:
                conn.executemany(
                    """INSERT INTO clean_sync_events (
                        id, customer_id_masked, timestamp, date, status, failure_category,
                        latency_ms, payload_size_bytes, retry_count, is_incident_window,
                        fingerprint, run_id, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    records_to_insert
                )

            # 3. Insert raw staging records
            raw_insert_rows = []
            for r in raw_records:
                raw_insert_rows.append((
                    r.get("id"),
                    run_id,
                    r.get("customer_id"),
                    r.get("timestamp"),
                    r.get("status"),
                    r.get("failure_category"),
                    r.get("latency_ms"),
                    r.get("payload_size_bytes"),
                    r.get("retry_count"),
                    json.dumps(r),
                    now_str
                ))
            if raw_insert_rows:
                conn.executemany(
                    """INSERT INTO raw_sync_events (
                        id, run_id, customer_id, timestamp, status, failure_category,
                        latency_ms, payload_size_bytes, retry_count, raw_json, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    raw_insert_rows
                )

            # 4. Insert rejected records dead-letter log
            rejected_rows = []
            for rej in rejected_records:
                r_orig = rej["record"]
                rejected_rows.append((
                    str(uuid.uuid4()),
                    run_id,
                    str(r_orig.get("id", "UNKNOWN_ID")),
                    json.dumps(r_orig),
                    rej["rejection_summary"],
                    now_str
                ))
            if rejected_rows:
                conn.executemany(
                    """INSERT INTO pipeline_rejected_records (
                        id, run_id, record_identifier, raw_data, rejection_reason, rejected_at
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                    rejected_rows
                )

        logger.info(
            f"Pipeline load committed: {len(records_to_insert)} inserted, {skipped_duplicates} duplicates skipped.",
            extra={"inserted": len(records_to_insert), "skipped_duplicates": skipped_duplicates}
        )
        return {
            "inserted": len(records_to_insert),
            "skipped_duplicates": skipped_duplicates,
            "raw_staged": len(raw_insert_rows),
            "rejected_logged": len(rejected_rows),
            "dry_run": False
        }
    finally:
        conn.close()

def record_pipeline_run_start(
    run_id: str,
    source: str,
    db_path: Path | str | None = None
) -> None:
    """Inserts an initial RUNNING status record into pipeline_runs."""
    target_path = Path(db_path) if db_path else config.db_path
    init_pipeline_schema(target_path)
    now_str = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(target_path))
    try:
        conn.execute(
            """INSERT INTO pipeline_runs (
                run_id, start_time, status, source, rows_extracted, rows_accepted,
                rows_rejected, rows_inserted, rows_updated, rows_skipped_duplicates
            ) VALUES (?, ?, 'RUNNING', ?, 0, 0, 0, 0, 0, 0)""",
            (run_id, now_str, source)
        )
        conn.commit()
    finally:
        conn.close()

def record_pipeline_run_finish(
    run_id: str,
    status: str,
    rows_extracted: int,
    rows_accepted: int,
    rows_rejected: int,
    rows_inserted: int,
    rows_skipped: int,
    error_summary: str | None = None,
    db_path: Path | str | None = None
) -> None:
    """Updates the pipeline_runs entry with final row counts and status."""
    target_path = Path(db_path) if db_path else config.db_path
    now_str = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(target_path))
    try:
        conn.execute(
            """UPDATE pipeline_runs SET
                finish_time = ?,
                status = ?,
                rows_extracted = ?,
                rows_accepted = ?,
                rows_rejected = ?,
                rows_inserted = ?,
                rows_skipped_duplicates = ?,
                error_summary = ?
            WHERE run_id = ?""",
            (now_str, status, rows_extracted, rows_accepted, rows_rejected, rows_inserted, rows_skipped, error_summary, run_id)
        )
        conn.commit()
    finally:
        conn.close()
