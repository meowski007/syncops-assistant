"""
Orchestration CLI and Runner for SyncOps ETL Pipeline.
Executes: Extract -> Validate -> Transform -> Load -> Report.
"""

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.config import config
from pipeline.extract import extract_data
from pipeline.validate import validate_dataset
from pipeline.transform import transform_records
from pipeline.load import (
    load_pipeline_data,
    record_pipeline_run_start,
    record_pipeline_run_finish,
)
from pipeline.report import record_quality_report
from app.incidents import list_incidents
from app.database import get_db
from app.logging_config import logger

def run_pipeline(
    source: str | None = None,
    db_path: Path | str | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    salt_override: str | None = None
) -> dict[str, Any]:
    """
    Executes complete reproducible ETL data pipeline:
    Extract -> Validate -> Transform -> Load -> Report.
    """
    target_db = Path(db_path) if db_path else config.db_path
    run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    source_label = source or f"sqlite://{target_db.name}/sync_events"
    
    if salt_override:
        config.pii_salt = salt_override

    print("=" * 65)
    print(f"🚀 SYNCOPS REPRODUCIBLE ETL PIPELINE [Run: {run_id}]")
    print(f"Source: {source_label} | Dry-Run: {dry_run}")
    print("=" * 65)

    if not dry_run:
        record_pipeline_run_start(run_id, source_label, db_path=target_db)

    try:
        # 1. EXTRACT
        print("\n[Phase 1: EXTRACT] Ingesting raw events...")
        extraction = extract_data(source=source, db_path=target_db)
        if limit and len(extraction.data) > limit:
            extraction.data = extraction.data[:limit]
            extraction.row_count = len(extraction.data)
        print(f"  ✓ Extracted {extraction.row_count} records from {extraction.source_description}")

        # 2. VALIDATE
        print("\n[Phase 2: VALIDATE] Executing schema & data quality checks...")
        accepted_raw, rejected_raw, val_summary = validate_dataset(extraction.data)
        print(f"  ✓ Accepted: {len(accepted_raw)} | Rejected: {len(rejected_raw)} | Warnings: {val_summary.warning_count}")
        if rejected_raw:
            print("  ⚠️  Sample rejections:")
            for rej in rejected_raw[:3]:
                print(f"     • {rej['rejection_summary']}")

        # 3. TRANSFORM
        print("\n[Phase 3: TRANSFORM] Normalizing, masking PII & deriving features...")
        # Query active incidents to correlate windows
        active_incs = []
        try:
            with get_db(target_db) as conn:
                active_incs = list_incidents(conn, limit=100)
        except Exception:
            pass

        clean_records, dup_in_batch = transform_records(accepted_raw, active_incidents=active_incs)
        print(f"  ✓ Transformed {len(clean_records)} clean records (Batch duplicates filtered: {dup_in_batch})")
        print(f"  ✓ PII Masking: customer_id -> {clean_records[0]['customer_id_masked'] if clean_records else 'N/A'}")

        # 4. LOAD
        print("\n[Phase 4: LOAD] Committing to SQLite (raw staging + clean analytical layers)...")
        load_stats = load_pipeline_data(
            run_id=run_id,
            source_desc=extraction.source_description,
            raw_records=extraction.data,
            clean_records=clean_records,
            rejected_records=rejected_raw,
            db_path=target_db,
            dry_run=dry_run
        )
        print(f"  ✓ Inserted new clean records: {load_stats['inserted']}")
        print(f"  ✓ Skipped historical duplicates: {load_stats['skipped_duplicates']}")
        print(f"  ✓ Staged raw audit events: {load_stats['raw_staged']}")

        # 5. REPORT
        print("\n[Phase 5: REPORT] Compiling audit report & quality metrics...")
        report_id = "DRY-RUN-REPORT"
        if not dry_run:
            report_id = record_quality_report(
                run_id=run_id,
                source_desc=extraction.source_description,
                summary=val_summary,
                load_stats=load_stats,
                db_path=target_db
            )
            record_pipeline_run_finish(
                run_id=run_id,
                status="SUCCESS" if val_summary.rejected_records == 0 else "WARNING",
                rows_extracted=extraction.row_count,
                rows_accepted=len(accepted_raw),
                rows_rejected=len(rejected_raw),
                rows_inserted=load_stats["inserted"],
                rows_skipped=load_stats["skipped_duplicates"],
                db_path=target_db
            )
        print(f"  ✓ Data Quality Report generated: {report_id}")
        
        print("\n" + "=" * 65)
        print(f"✅ PIPELINE RUN COMPLETED SUCCESSFULLY! [Run: {run_id}]")
        print("=" * 65)
        
        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "extracted": extraction.row_count,
            "accepted": len(accepted_raw),
            "rejected": len(rejected_raw),
            "inserted": load_stats["inserted"],
            "skipped_duplicates": load_stats["skipped_duplicates"],
            "report_id": report_id
        }

    except Exception as exc:
        logger.error(f"Pipeline run {run_id} failed: {exc}", exc_info=True)
        if not dry_run:
            record_pipeline_run_finish(
                run_id=run_id,
                status="FAILED",
                rows_extracted=0,
                rows_accepted=0,
                rows_rejected=0,
                rows_inserted=0,
                rows_skipped=0,
                error_summary=str(exc),
                db_path=target_db
            )
        print(f"\n❌ PIPELINE EXECUTION FAILED: {exc}")
        raise exc

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SyncOps Reproducible ETL Pipeline Runner")
    parser.add_argument("--source", type=str, default=None, help="Input source (CSV file path, table name, or synthetic://stream)")
    parser.add_argument("--db", type=str, default=None, help="Target SQLite database path")
    parser.add_argument("--dry-run", action="store_true", help="Execute validation and transformations without writing to database")
    parser.add_argument("--limit", type=int, default=None, help="Maximum rows to process")
    parser.add_argument("--salt", type=str, default=None, help="PII masking salt override")
    args = parser.parse_args()

    run_pipeline(
        source=args.source,
        db_path=args.db,
        dry_run=args.dry_run,
        limit=args.limit,
        salt_override=args.salt
    )
