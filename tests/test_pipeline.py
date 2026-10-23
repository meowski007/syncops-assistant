"""Tests for ETL Pipeline: Extraction, Validation, Transformation, Idempotent Loading."""

import sqlite3
import pytest
from pathlib import Path
from pipeline.config import config
from pipeline.extract import extract_from_sqlite, extract_synthetic_stream, extract_data
from pipeline.validate import validate_single_record, validate_dataset
from pipeline.transform import mask_customer_id, compute_record_fingerprint, transform_records
from pipeline.load import load_pipeline_data, init_pipeline_schema
from pipeline.run import run_pipeline
from scripts.seed_data import seed_database

@pytest.fixture
def temp_pipeline_db(tmp_path):
    db_file = tmp_path / "test_pipeline.db"
    seed_database(db_path=db_file)
    init_pipeline_schema(db_file)
    return db_file

def test_extract_from_sqlite(temp_pipeline_db):
    res = extract_from_sqlite(db_path=temp_pipeline_db, limit=50)
    assert res.row_count == 50
    assert len(res.data) == 50
    assert "sqlite://" in res.source_description

def test_extract_synthetic_stream():
    res = extract_synthetic_stream(count=25, seed=123)
    assert res.row_count == 25
    assert res.data[0]["status"] in ("SUCCESS", "FAILURE")

def test_transform_pii_masking():
    raw_cust = "CUST-9999"
    masked1 = mask_customer_id(raw_cust, salt="SALT_A")
    masked2 = mask_customer_id(raw_cust, salt="SALT_A")
    masked3 = mask_customer_id(raw_cust, salt="SALT_B")
    
    assert masked1.startswith("MASK-")
    assert masked1 == masked2  # Deterministic with same salt
    assert masked1 != masked3  # Salt changes the digest

def test_transform_fingerprint_deterministic():
    rec = {
        "id": "EVT-1234",
        "customer_id": "CUST-0001",
        "timestamp": "2026-10-23T12:00:00Z",
        "status": "SUCCESS",
        "latency_ms": 150.0
    }
    fp1 = compute_record_fingerprint(rec)
    fp2 = compute_record_fingerprint(rec)
    assert fp1 == fp2
    assert len(fp1) == 64

def test_transform_records_deduplication():
    records = [
        {"id": "EVT-001", "customer_id": "CUST-1", "timestamp": "2026-10-23T10:00:00Z", "status": "SUCCESS", "latency_ms": 100, "payload_size_bytes": 1024},
        {"id": "EVT-001", "customer_id": "CUST-1", "timestamp": "2026-10-23T10:00:00Z", "status": "SUCCESS", "latency_ms": 100, "payload_size_bytes": 1024},
        {"id": "EVT-002", "customer_id": "CUST-2", "timestamp": "2026-10-23T11:00:00Z", "status": "FAILURE", "latency_ms": 800, "payload_size_bytes": 2048, "failure_category": "AUTH_EXPIRED"},
    ]
    clean, dup_count = transform_records(records)
    assert len(clean) == 2
    assert dup_count == 1
    assert clean[0]["id"] == "EVT-001"
    assert clean[1]["id"] == "EVT-002"

def test_idempotent_loading_repeated_runs(temp_pipeline_db):
    # Run 1: Ingest 100 records
    res1 = run_pipeline(
        source=f"synthetic://stream?count=100&seed=99",
        db_path=temp_pipeline_db
    )
    assert res1["status"] == "SUCCESS"
    assert res1["inserted"] == 100
    assert res1["skipped_duplicates"] == 0

    # Run 2: Re-ingest exact same 100 records
    res2 = run_pipeline(
        source=f"synthetic://stream?count=100&seed=99",
        db_path=temp_pipeline_db
    )
    assert res2["status"] == "SUCCESS"
    assert res2["inserted"] == 0
    assert res2["skipped_duplicates"] == 100

    # Verify database total row count remains exactly 100
    conn = sqlite3.connect(str(temp_pipeline_db))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clean_sync_events WHERE id LIKE 'EXT-STREAM-99%'")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 100

def test_pipeline_dry_run_no_writes(temp_pipeline_db):
    res = run_pipeline(
        source="synthetic://stream?count=50&seed=777",
        db_path=temp_pipeline_db,
        dry_run=True
    )
    assert res["status"] == "SUCCESS"
    assert res["inserted"] == 0
    
    conn = sqlite3.connect(str(temp_pipeline_db))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clean_sync_events WHERE id LIKE 'EXT-STREAM-777%'")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0
