"""Transformation and PII Pseudonymization module for SyncOps ETL pipeline."""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any
from pipeline.config import config
from app.logging_config import logger

_warned_dev_salt = False

def mask_customer_id(customer_id: str, salt: str | None = None) -> str:
    """
    Pseudonymizes customer identifiers using HMAC-SHA256 with a configurable salt.
    
    SECURITY & PRIVACY DISCLOSURE:
    This is deterministic pseudonymization, NOT true irreversible anonymization.
    Deterministic hashes can still be linked across records and could theoretically
    be vulnerable to dictionary/rainbow table attacks if the customer ID keyspace is small.
    A secret high-entropy salt must be provided via the PII_SALT environment variable in production.
    """
    global _warned_dev_salt
    effective_salt = salt or config.pii_salt
    if not config.is_production_salt and not _warned_dev_salt:
        logger.warning(
            "Using default development salt for PII masking. "
            "Set PII_SALT or PII_HMAC_KEY in production to ensure cryptographic separation."
        )
        _warned_dev_salt = True
    
    key_bytes = effective_salt.encode("utf-8")
    data_bytes = customer_id.strip().encode("utf-8")
    digest = hmac.new(key_bytes, data_bytes, hashlib.sha256).hexdigest()
    return f"MASK-{digest[:16]}"

def compute_record_fingerprint(record: dict[str, Any]) -> str:
    """
    Computes a deterministic content fingerprint for deduplication.
    Uses canonical ordered fields: id, customer_id, timestamp, status, latency_ms.
    """
    canonical_str = (
        f"{str(record.get('id', '')).strip()}|"
        f"{str(record.get('customer_id', '')).strip()}|"
        f"{str(record.get('timestamp', '')).strip()}|"
        f"{str(record.get('status', '')).strip().upper()}|"
        f"{float(record.get('latency_ms', 0.0)):.2f}"
    )
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

def transform_records(
    valid_records: list[dict[str, Any]],
    active_incidents: list[dict[str, Any]] | None = None
) -> tuple[list[dict[str, Any]], int]:
    """
    Transforms validated records into clean analytical format:
    - Normalizes types and categories
    - Replaces customer_id with masked pseudonym
    - Extracts date partition key
    - Correlates with incident windows
    - Preserves deterministic input ordering (no unordered sets)
    
    Returns (clean_records, duplicates_in_batch_count).
    """
    clean_records: list[dict[str, Any]] = []
    seen_ids: dict[str, bool] = {}  # Preserves insertion order
    duplicate_count = 0
    
    incident_windows = []
    if active_incidents:
        for inc in active_incidents:
            try:
                st = datetime.fromisoformat(inc["start_time"].replace("Z", "+00:00"))
                rt = datetime.fromisoformat(inc["recovery_time"].replace("Z", "+00:00")) if inc.get("recovery_time") else None
                incident_windows.append((st, rt, inc.get("affected_cohort")))
            except Exception:
                pass

    for r in valid_records:
        rec_id = str(r["id"]).strip()
        
        # Batch-level deduplication preserving order
        if rec_id in seen_ids:
            duplicate_count += 1
            continue
        seen_ids[rec_id] = True
        
        # 1. Normalize timestamp & extract date partition
        raw_ts = str(r["timestamp"]).strip()
        if raw_ts.endswith("Z"):
            raw_ts = raw_ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        normalized_ts = dt.isoformat()
        date_str = dt.strftime("%Y-%m-%d")
        
        # 2. Normalize status & category
        status_norm = str(r["status"]).strip().upper()
        raw_cat = r.get("failure_category")
        if status_norm == "SUCCESS":
            cat_norm = None
        else:
            cat_norm = str(raw_cat).strip().upper() if raw_cat else "UNKNOWN_FAILURE"
            
        # 3. Numeric casts
        latency_val = round(float(r["latency_ms"]), 2)
        payload_val = int(r["payload_size_bytes"])
        retry_val = int(r.get("retry_count", 0) or 0)
        
        # 4. PII Masking for analytical layer
        raw_customer = str(r["customer_id"]).strip()
        masked_customer = mask_customer_id(raw_customer)
        
        # 5. Derived feature: Incident window indicator
        is_incident_window = 0
        for st, rt, _ in incident_windows:
            if rt:
                if st <= dt <= rt:
                    is_incident_window = 1
                    break
            else:
                if st <= dt:
                    is_incident_window = 1
                    break

        clean_item = {
            "id": rec_id,
            "raw_customer_id": raw_customer,  # retained for raw layer staging
            "customer_id_masked": masked_customer,
            "timestamp": normalized_ts,
            "date": date_str,
            "status": status_norm,
            "failure_category": cat_norm,
            "latency_ms": latency_val,
            "payload_size_bytes": payload_val,
            "retry_count": retry_val,
            "is_incident_window": is_incident_window,
            "fingerprint": compute_record_fingerprint(r)
        }
        clean_records.append(clean_item)

    return clean_records, duplicate_count
