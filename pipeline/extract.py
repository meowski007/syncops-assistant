"""Extraction module for the SyncOps ETL pipeline."""

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

from pipeline.config import config
from app.logging_config import logger

class ExtractionResult:
    def __init__(self, data: list[dict[str, Any]], source_description: str, row_count: int):
        self.data = data
        self.source_description = source_description
        self.row_count = row_count
        self.extracted_at = datetime.now(timezone.utc).isoformat()

def extract_from_sqlite(db_path: Path | str | None = None, table_name: str = "sync_events", limit: int | None = None) -> ExtractionResult:
    """Extracts raw synchronization events from an SQLite database table."""
    target_path = Path(db_path) if db_path else config.db_path
    if not target_path.exists():
        raise FileNotFoundError(f"Source database file not found at: {target_path}")

    query = f"SELECT * FROM {table_name}"
    if limit is not None:
        query += f" LIMIT {int(limit)}"

    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]
        source_desc = f"sqlite://{target_path.name}/{table_name}"
        logger.info(f"Extracted {len(rows)} records from {source_desc}")
        return ExtractionResult(data=rows, source_description=source_desc, row_count=len(rows))
    finally:
        conn.close()

def extract_from_csv(csv_path: Path | str) -> ExtractionResult:
    """Extracts raw synchronization events from a CSV file."""
    target_path = Path(csv_path)
    if not target_path.exists():
        raise FileNotFoundError(f"Input CSV file not found at: {target_path}")

    df = pd.read_csv(target_path)
    rows = df.to_dict(orient="records")
    source_desc = f"csv://{target_path.name}"
    logger.info(f"Extracted {len(rows)} records from {source_desc}")
    return ExtractionResult(data=rows, source_description=source_desc, row_count=len(rows))

def extract_synthetic_stream(count: int = 100, seed: int = 42) -> ExtractionResult:
    """
    Deterministic synthetic data extractor for testing and streaming ingestion
    without requiring an external file.
    """
    import random
    from datetime import timedelta
    random.seed(seed)
    now = datetime.now(timezone.utc)
    
    categories = ["PAYLOAD_TIMEOUT", "AUTH_EXPIRED", "SCHEMA_MISMATCH", "RATE_LIMITED", "DATABASE_LOCK", "FIRMWARE_UNSUPPORTED"]
    
    records = []
    for i in range(1, count + 1):
        is_success = random.random() < 0.94
        event_time = now - timedelta(hours=random.uniform(0.1, 72.0))
        records.append({
            "id": f"EXT-STREAM-{seed}-{i:05d}",
            "customer_id": f"CUST-{random.randint(1, 300):04d}",
            "timestamp": event_time.isoformat(),
            "status": "SUCCESS" if is_success else "FAILURE",
            "failure_category": None if is_success else random.choice(categories),
            "latency_ms": round(random.uniform(50.0, 500.0) if is_success else random.uniform(800.0, 5000.0), 2),
            "payload_size_bytes": random.randint(1024, 65536),
            "retry_count": 0 if is_success else random.choice([1, 2, 3])
        })
    source_desc = f"synthetic://stream?count={count}&seed={seed}"
    return ExtractionResult(data=records, source_description=source_desc, row_count=len(records))

def extract_data(source: str | Path | None = None, db_path: Path | str | None = None) -> ExtractionResult:
    """Unified extractor router supporting files, SQLite tables, or synthetic generator."""
    if source is None:
        return extract_from_sqlite(db_path=db_path)
    
    source_str = str(source)
    if source_str.endswith(".csv"):
        return extract_from_csv(source)
    elif source_str.startswith("synthetic://"):
        count = 100
        seed = 42
        if "count=" in source_str:
            try:
                count = int(source_str.split("count=")[1].split("&")[0])
            except Exception:
                pass
        if "seed=" in source_str:
            try:
                seed = int(source_str.split("seed=")[1].split("&")[0])
            except Exception:
                pass
        return extract_synthetic_stream(count=count, seed=seed)
    else:
        # Default assume SQLite path or table name
        if Path(source_str).exists() and source_str.endswith(".db"):
            return extract_from_sqlite(db_path=source_str)
        return extract_from_sqlite(db_path=db_path, table_name=source_str)
