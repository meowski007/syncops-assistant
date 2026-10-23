# SRE Runbook: Data Quality & Schema Validation Failures

## Overview
- **Category:** `DATA_QUALITY_FAILURE` / `SCHEMA_MISMATCH`
- **Severity Classification:** SEV2 (Rejection rate > 10% of batch) / SEV3 (Isolated schema violations)
- **Service:** ETL Ingestion Pipeline & Quality Gatekeeper
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `PipelineDataQualityRejectionSpike`: Ingestion rejection count exceeds 5.0% of batch records.
- Automated data quality audit reports indicate status `FAILED` or `WARNING`.
- High volume of entries written to `pipeline_rejected_records`.

## 2. Immediate Diagnostic Checklist
1. **Query Rejection Breakdown:**
   - Execute query on `data_quality_reports` to inspect `rejection_breakdown_json`.
   - Check if errors are concentrated in `MISSING_REQUIRED_FIELD`, `INVALID_STATUS_VALUE`, or `FUTURE_TIMESTAMP_VIOLATION`.
2. **Correlate with Source Cohorts:**
   - Check if rejected records originate from a new partner CSV export or an untested beta client build.
3. **Verify Timestamp Clock Skew:**
   - Confirm whether client devices have drifted outside the permitted 1-hour future tolerance window.

## 3. Mitigation Steps
1. **Quarantine Erroneous Records:**
   - Confirm that blocking validation rules successfully isolated invalid payloads from `clean_sync_events`.
2. **Deploy Schema Patch:**
   - If a new valid attribute was added by upstream clients, update `pipeline/validate.py` schema catalog to permit the field.
3. **Trigger Pipeline Reprocessing:**
   - Once schema or client fix is deployed, execute `python -m pipeline.run --source <source>` to ingest corrected records.

## 4. Rollback Strategy
- If a pipeline update inadvertently introduced false-positive rejections, revert `pipeline/validate.py` rules.

## 5. Verification & Recovery Confirmation
- Pipeline execution completes with 100% accepted records and zero blocking rejections.
- Data quality report status returns to `🟢 PASSED`.
