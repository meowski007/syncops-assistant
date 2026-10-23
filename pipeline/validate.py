"""Validation and Data Quality checks for the SyncOps ETL pipeline."""

from datetime import datetime, timezone, timedelta
from typing import Any
import pandas as pd

from pipeline.config import config
from app.logging_config import logger

VALID_STATUSES = {"SUCCESS", "FAILURE"}
ALLOWED_FAILURE_CATEGORIES = {
    "PAYLOAD_TIMEOUT",
    "AUTH_EXPIRED",
    "SCHEMA_MISMATCH",
    "RATE_LIMITED",
    "DATABASE_LOCK",
    "FIRMWARE_UNSUPPORTED",
}

class ValidationRecord:
    def __init__(self, record: dict[str, Any], is_valid: bool, rejection_reasons: list[str], warnings: list[str]):
        self.record = record
        self.is_valid = is_valid
        self.rejection_reasons = rejection_reasons
        self.warnings = warnings

class ValidationReportSummary:
    def __init__(
        self,
        total_records: int,
        accepted_records: int,
        rejected_records: int,
        warning_count: int,
        rejection_breakdown: dict[str, int],
        warning_breakdown: dict[str, int],
        check_details: list[dict[str, Any]],
    ):
        self.total_records = total_records
        self.accepted_records = accepted_records
        self.rejected_records = rejected_records
        self.warning_count = warning_count
        self.rejection_breakdown = rejection_breakdown
        self.warning_breakdown = warning_breakdown
        self.check_details = check_details
        self.passed = (rejected_records == 0)

def validate_single_record(
    record: dict[str, Any],
    now_utc: datetime | None = None
) -> tuple[bool, list[str], list[str]]:
    """
    Validates a single sync event record against blocking and non-blocking rules.
    Returns (is_valid, rejection_reasons, warnings).
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
        
    rejections = []
    warnings = []
    
    # 1. Required Fields Check (Blocking)
    required_fields = ["id", "customer_id", "timestamp", "status", "latency_ms", "payload_size_bytes"]
    for field in required_fields:
        val = record.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            rejections.append(f"MISSING_REQUIRED_FIELD:{field}")

    # If missing fundamental identity fields, return early
    if rejections:
        return False, rejections, warnings

    # 2. Event ID Validation (Blocking)
    event_id = str(record["id"]).strip()
    if len(event_id) < 3 or not any(c.isalnum() for c in event_id):
        rejections.append(f"INVALID_EVENT_ID_FORMAT:{event_id}")

    # 3. Status Validation (Blocking)
    raw_status = str(record.get("status", "")).strip().upper()
    if raw_status not in VALID_STATUSES:
        rejections.append(f"INVALID_STATUS_VALUE:{raw_status}")

    # 4. Latency Bounds (Blocking if < 0; Warning if > 10,000ms)
    try:
        latency = float(record["latency_ms"])
        if latency < 0.0:
            rejections.append("NEGATIVE_LATENCY_NOT_PERMITTED")
        elif latency > config.max_latency_ms:
            rejections.append(f"EXCESSIVE_LATENCY_OUTLIER:{latency}ms")
        elif latency > 10000.0:
            warnings.append(f"HIGH_LATENCY_WARNING:{latency}ms")
    except (ValueError, TypeError):
        rejections.append("NON_NUMERIC_LATENCY")

    # 5. Payload Size Bounds (Blocking if < 0; Warning if > 1MB)
    try:
        payload_size = int(record["payload_size_bytes"])
        if payload_size < 0:
            rejections.append("NEGATIVE_PAYLOAD_SIZE_NOT_PERMITTED")
        elif payload_size > config.max_payload_bytes:
            rejections.append(f"EXCESSIVE_PAYLOAD_SIZE:{payload_size}_bytes")
        elif payload_size > 1024 * 1024:
            warnings.append(f"LARGE_PAYLOAD_WARNING:{payload_size}_bytes")
    except (ValueError, TypeError):
        rejections.append("NON_INTEGER_PAYLOAD_SIZE")

    # 6. Retry Count Validation
    retry_count = record.get("retry_count", 0)
    try:
        retries = int(retry_count) if retry_count is not None else 0
        if retries < 0:
            rejections.append("NEGATIVE_RETRY_COUNT")
        elif retries > 5:
            warnings.append(f"HIGH_RETRY_COUNT_WARNING:{retries}")
    except (ValueError, TypeError):
        rejections.append("NON_INTEGER_RETRY_COUNT")

    # 7. Timestamp Sanity & Future Drift (Blocking)
    raw_ts = str(record["timestamp"]).strip()
    try:
        # Standardize ISO parse
        if raw_ts.endswith("Z"):
            raw_ts = raw_ts[:-1] + "+00:00"
        ts_dt = datetime.fromisoformat(raw_ts)
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
            
        future_cutoff = now_utc + timedelta(seconds=config.max_future_seconds_allowed)
        if ts_dt > future_cutoff:
            drift_sec = int((ts_dt - now_utc).total_seconds())
            rejections.append(f"FUTURE_TIMESTAMP_VIOLATION:ahead_by_{drift_sec}s")
            
        # Far past timestamp check (> 365 days past)
        past_cutoff = now_utc - timedelta(days=365)
        if ts_dt < past_cutoff:
            warnings.append(f"STALE_HISTORICAL_TIMESTAMP:{raw_ts}")
    except Exception as e:
        rejections.append(f"UNPARSEABLE_TIMESTAMP:{raw_ts}_error:{e}")

    # 8. Category Consistency Warning
    cat = record.get("failure_category")
    if raw_status == "FAILURE" and (cat is None or str(cat).strip().lower() in ("none", "null", "")):
        warnings.append("FAILURE_WITHOUT_CATEGORY")

    is_valid = (len(rejections) == 0)
    return is_valid, rejections, warnings

def validate_dataset(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], ValidationReportSummary]:
    """
    Validates a list of records, returning (accepted_records, rejected_records_with_metadata, summary_report).
    """
    now_utc = datetime.now(timezone.utc)
    accepted = []
    rejected = []
    
    rejection_counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    
    check_catalog = [
        {"name": "required_columns", "type": "BLOCKING", "description": "Ensure id, customer_id, timestamp, status, latency, payload exist."},
        {"name": "status_allowed_values", "type": "BLOCKING", "description": "Ensure status is in ('SUCCESS', 'FAILURE')."},
        {"name": "non_negative_metrics", "type": "BLOCKING", "description": "Ensure latency_ms >= 0 and payload_size_bytes >= 0."},
        {"name": "timestamp_clock_skew", "type": "BLOCKING", "description": "Ensure timestamp is within +1h future tolerance."},
        {"name": "latency_outlier_warning", "type": "WARNING", "description": "Flag sync events exceeding 10,000ms latency."},
        {"name": "retry_outlier_warning", "type": "WARNING", "description": "Flag sync attempts with retry_count > 5."},
    ]
    
    for r in records:
        is_valid, rejections, warnings = validate_single_record(r, now_utc=now_utc)
        
        for w in warnings:
            w_code = w.split(":")[0]
            warning_counts[w_code] = warning_counts.get(w_code, 0) + 1
            
        if is_valid:
            accepted.append(r)
        else:
            for r_reason in rejections:
                r_code = r_reason.split(":")[0]
                rejection_counts[r_code] = rejection_counts.get(r_code, 0) + 1
            rejected.append({
                "record": r,
                "reasons": rejections,
                "rejection_summary": "; ".join(rejections)
            })

    total_warnings = sum(warning_counts.values())
    summary = ValidationReportSummary(
        total_records=len(records),
        accepted_records=len(accepted),
        rejected_records=len(rejected),
        warning_count=total_warnings,
        rejection_breakdown=rejection_counts,
        warning_breakdown=warning_counts,
        check_details=check_catalog,
    )
    
    logger.info(
        f"Validation complete: {len(accepted)} accepted, {len(rejected)} rejected, {total_warnings} warnings.",
        extra={"accepted": len(accepted), "rejected": len(rejected)}
    )
    return accepted, rejected, summary
