"""Tests for Data Quality checks, deliberate failure rejection, and report generation."""

from datetime import datetime, timedelta, timezone
from pipeline.validate import validate_single_record, validate_dataset
from pipeline.report import generate_quality_markdown_report, ValidationReportSummary

def test_dq_blocking_missing_required_fields():
    bad_record = {
        "id": "EVT-BAD-01",
        "timestamp": "2026-10-23T12:00:00Z",
        # missing customer_id, status, latency_ms, payload_size_bytes
    }
    is_valid, rejections, warnings = validate_single_record(bad_record)
    assert is_valid is False
    assert any("MISSING_REQUIRED_FIELD:customer_id" in r for r in rejections)
    assert any("MISSING_REQUIRED_FIELD:status" in r for r in rejections)

def test_dq_blocking_invalid_status():
    bad_record = {
        "id": "EVT-BAD-02",
        "customer_id": "CUST-001",
        "timestamp": "2026-10-23T12:00:00Z",
        "status": "UNKNOWN_STATUS",
        "latency_ms": 100,
        "payload_size_bytes": 1024
    }
    is_valid, rejections, warnings = validate_single_record(bad_record)
    assert is_valid is False
    assert any("INVALID_STATUS_VALUE:UNKNOWN_STATUS" in r for r in rejections)

def test_dq_blocking_negative_metrics():
    bad_record = {
        "id": "EVT-BAD-03",
        "customer_id": "CUST-001",
        "timestamp": "2026-10-23T12:00:00Z",
        "status": "SUCCESS",
        "latency_ms": -50.0,
        "payload_size_bytes": -200
    }
    is_valid, rejections, warnings = validate_single_record(bad_record)
    assert is_valid is False
    assert "NEGATIVE_LATENCY_NOT_PERMITTED" in rejections
    assert "NEGATIVE_PAYLOAD_SIZE_NOT_PERMITTED" in rejections

def test_dq_blocking_future_timestamp_violation():
    now_utc = datetime.now(timezone.utc)
    far_future = (now_utc + timedelta(days=2)).isoformat()
    bad_record = {
        "id": "EVT-BAD-04",
        "customer_id": "CUST-001",
        "timestamp": far_future,
        "status": "SUCCESS",
        "latency_ms": 100,
        "payload_size_bytes": 1024
    }
    is_valid, rejections, warnings = validate_single_record(bad_record, now_utc=now_utc)
    assert is_valid is False
    assert any("FUTURE_TIMESTAMP_VIOLATION" in r for r in rejections)

def test_dq_non_blocking_warnings():
    warn_record = {
        "id": "EVT-WARN-01",
        "customer_id": "CUST-001",
        "timestamp": "2026-10-23T12:00:00Z",
        "status": "FAILURE",
        "failure_category": None,  # Warning: failure without category
        "latency_ms": 15000.0,     # Warning: latency > 10,000ms
        "payload_size_bytes": 2 * 1024 * 1024, # Warning: payload > 1MB
        "retry_count": 8           # Warning: retry > 5
    }
    is_valid, rejections, warnings = validate_single_record(warn_record)
    # Warnings are NON-BLOCKING so record is valid
    assert is_valid is True
    assert len(rejections) == 0
    assert any("HIGH_LATENCY_WARNING" in w for w in warnings)
    assert any("LARGE_PAYLOAD_WARNING" in w for w in warnings)
    assert any("HIGH_RETRY_COUNT_WARNING" in w for w in warnings)
    assert any("FAILURE_WITHOUT_CATEGORY" in w for w in warnings)

def test_dq_dataset_rejection_separation():
    records = [
        {"id": "EVT-GOOD-1", "customer_id": "CUST-1", "timestamp": "2026-10-23T12:00:00Z", "status": "SUCCESS", "latency_ms": 100, "payload_size_bytes": 1024},
        {"id": "EVT-BAD-1", "customer_id": "CUST-2", "timestamp": "2026-10-23T12:00:00Z", "status": "INVALID", "latency_ms": -10, "payload_size_bytes": 1024},
    ]
    accepted, rejected, summary = validate_dataset(records)
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["record"]["id"] == "EVT-BAD-1"
    assert summary.total_records == 2
    assert summary.rejected_records == 1
    assert summary.passed is False

def test_dq_markdown_report_generation(tmp_path):
    summary = ValidationReportSummary(
        total_records=100,
        accepted_records=95,
        rejected_records=5,
        warning_count=3,
        rejection_breakdown={"INVALID_STATUS_VALUE": 5},
        warning_breakdown={"HIGH_LATENCY_WARNING": 3},
        check_details=[{"name": "test_check", "type": "BLOCKING", "description": "test"}],
    )
    load_stats = {"inserted": 95, "skipped_duplicates": 0, "dry_run": False}
    
    report_file = generate_quality_markdown_report(
        run_id="TEST-RUN-001",
        source_desc="test_source",
        summary=summary,
        load_stats=load_stats,
        reports_dir=tmp_path
    )
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "TEST-RUN-001" in content
    assert "INVALID_STATUS_VALUE" in content
    assert "HIGH_LATENCY_WARNING" in content
    assert "BLOCKING REJECTIONS DETECTED" in content
